#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import json
import os
import re
import logging
import httpx
import asyncio
from datetime import timedelta
from copy import deepcopy
import tempfile
from quart import Response, request, make_response
from api.apps import current_user, login_required
from api.db.db_models import APIToken
from api.db.services.conversation_service import ConversationService, structure_answer
from api.db.services.dialog_service import DialogService, async_ask, async_chat, gen_mindmap
from api.db.services.llm_service import LLMBundle
from api.db.services.search_service import SearchService
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.user_service import TenantService, UserTenantService
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json, server_error_response, validate_request
from rag.prompts.template import load_prompt
from rag.prompts.generator import chunks_format
from rag.utils.minio_conn import RAGFlowMinio
from common.constants import RetCode, LLMType
from common import settings

TTS_API_URL = "http://127.0.0.1:8001/submit_tts_task"
CALLBACK_URL = "http://127.0.0.1:9380/v1/conversation/tts/callback"
minio_client = RAGFlowMinio()


@manager.route("/set", methods=["POST"])  # noqa: F821
@login_required
async def set_conversation():
    req = await get_request_json()
    conv_id = req.get("conversation_id")
    is_new = req.get("is_new")
    name = req.get("name", "New conversation")
    req["user_id"] = current_user.id

    if len(name) > 255:
        name = name[0:255]

    del req["is_new"]
    if not is_new:
        del req["conversation_id"]
        try:
            if not ConversationService.update_by_id(conv_id, req):
                return get_data_error_result(message="Conversation not found!")
            e, conv = ConversationService.get_by_id(conv_id)
            if not e:
                return get_data_error_result(message="Fail to update a conversation!")
            conv = conv.to_dict()
            return get_json_result(data=conv)
        except Exception as e:
            return server_error_response(e)

    try:
        e, dia = DialogService.get_by_id(req["dialog_id"])
        if not e:
            return get_data_error_result(message="Dialog not found")
        conv = {
            "id": conv_id,
            "dialog_id": req["dialog_id"],
            "name": name,
            "message": [{"role": "assistant", "content": dia.prompt_config["prologue"]}],
            "user_id": current_user.id,
            "reference": [],
        }
        ConversationService.save(**conv)
        return get_json_result(data=conv)
    except Exception as e:
        return server_error_response(e)


@manager.route("/get", methods=["GET"])  # noqa: F821
@login_required
async def get():
    conv_id = request.args["conversation_id"]
    try:
        e, conv = ConversationService.get_by_id(conv_id)
        if not e:
            return get_data_error_result(message="Conversation not found!")
        tenants = UserTenantService.query(user_id=current_user.id)
        for tenant in tenants:
            dialog = DialogService.query(tenant_id=tenant.tenant_id, id=conv.dialog_id)
            if dialog and len(dialog) > 0:
                avatar = dialog[0].icon
                break
        else:
            return get_json_result(data=False, message="Only owner of conversation authorized for this operation.", code=RetCode.OPERATING_ERROR)

        for ref in conv.reference:
            if isinstance(ref, list):
                continue
            ref["chunks"] = chunks_format(ref)

        conv = conv.to_dict()
        conv["avatar"] = avatar
        return get_json_result(data=conv)
    except Exception as e:
        return server_error_response(e)


@manager.route("/getsse/<dialog_id>", methods=["GET"])  # type: ignore # noqa: F821
def getsse(dialog_id):
    token = request.headers.get("Authorization").split()
    if len(token) != 2:
        return get_data_error_result(message='Authorization is not valid!"')
    token = token[1]
    objs = APIToken.query(beta=token)
    if not objs:
        return get_data_error_result(message='Authentication error: API key is invalid!"')
    try:
        e, conv = DialogService.get_by_id(dialog_id)
        if not e:
            return get_data_error_result(message="Dialog not found!")
        conv = conv.to_dict()
        conv["avatar"] = conv["icon"]
        del conv["icon"]
        return get_json_result(data=conv)
    except Exception as e:
        return server_error_response(e)


@manager.route("/rm", methods=["POST"])  # noqa: F821
@login_required
async def rm():
    req = await get_request_json()
    conv_ids = req["conversation_ids"]
    try:
        for cid in conv_ids:
            exist, conv = ConversationService.get_by_id(cid)
            if not exist:
                return get_data_error_result(message="Conversation not found!")
            tenants = UserTenantService.query(user_id=current_user.id)
            for tenant in tenants:
                if DialogService.query(tenant_id=tenant.tenant_id, id=conv.dialog_id):
                    break
            else:
                return get_json_result(data=False, message="Only owner of conversation authorized for this operation.", code=RetCode.OPERATING_ERROR)
            ConversationService.delete_by_id(cid)
        return get_json_result(data=True)
    except Exception as e:
        return server_error_response(e)


@manager.route("/list", methods=["GET"])  # noqa: F821
@login_required
async def list_conversation():
    dialog_id = request.args["dialog_id"]
    try:
        if not DialogService.query(tenant_id=current_user.id, id=dialog_id):
            return get_json_result(data=False, message="Only owner of dialog authorized for this operation.", code=RetCode.OPERATING_ERROR)
        convs = ConversationService.query(dialog_id=dialog_id, order_by=ConversationService.model.create_time, reverse=True)

        convs = [d.to_dict() for d in convs]
        return get_json_result(data=convs)
    except Exception as e:
        return server_error_response(e)


@manager.route("/completion", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "messages")
async def completion():
    req = await get_request_json()
    msg = []
    for m in req["messages"]:
        if m["role"] == "system":
            continue
        if m["role"] == "assistant" and not msg:
            continue
        msg.append(m)
    message_id = msg[-1].get("id")
    chat_model_id = req.get("llm_id", "")
    req.pop("llm_id", None)

    chat_model_config = {}
    for model_config in [
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
        "max_tokens",
    ]:
        config = req.get(model_config)
        if config:
            chat_model_config[model_config] = config

    try:
        e, conv = ConversationService.get_by_id(req["conversation_id"])
        if not e:
            return get_data_error_result(message="Conversation not found!")
        conv.message = deepcopy(req["messages"])
        e, dia = DialogService.get_by_id(conv.dialog_id)
        if not e:
            return get_data_error_result(message="Dialog not found!")
        del req["conversation_id"]
        del req["messages"]

        if not conv.reference:
            conv.reference = []
        conv.reference = [r for r in conv.reference if r]
        conv.reference.append({"chunks": [], "doc_aggs": []})

        if chat_model_id:
            if not TenantLLMService.get_api_key(tenant_id=dia.tenant_id, model_name=chat_model_id):
                req.pop("chat_model_id", None)
                req.pop("chat_model_config", None)
                return get_data_error_result(message=f"Cannot use specified model {chat_model_id}.")
            dia.llm_id = chat_model_id
            dia.llm_setting = chat_model_config

        is_embedded = bool(chat_model_id)
        async def stream():
            nonlocal dia, msg, req, conv
            try:
                async for ans in async_chat(dia, msg, True, **req):
                    ans = structure_answer(conv, ans, message_id, conv.id)
                    yield "data:" + json.dumps({"code": 0, "message": "", "data": ans}, ensure_ascii=False) + "\n\n"
                if not is_embedded:
                    ConversationService.update_by_id(conv.id, conv.to_dict())
            except Exception as e:
                logging.exception(e)
                yield "data:" + json.dumps({"code": 500, "message": str(e), "data": {"answer": "**ERROR**: " + str(e), "reference": []}}, ensure_ascii=False) + "\n\n"
            yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"

        if req.get("stream", True):
            resp = Response(stream(), mimetype="text/event-stream")
            resp.headers.add_header("Cache-control", "no-cache")
            resp.headers.add_header("Connection", "keep-alive")
            resp.headers.add_header("X-Accel-Buffering", "no")
            resp.headers.add_header("Content-Type", "text/event-stream; charset=utf-8")
            return resp

        else:
            answer = None
            async for ans in async_chat(dia, msg, **req):
                answer = structure_answer(conv, ans, message_id, conv.id)
                if not is_embedded:
                    ConversationService.update_by_id(conv.id, conv.to_dict())
                break
            return get_json_result(data=answer)
    except Exception as e:
        return server_error_response(e)

@manager.route("/sequence2txt", methods=["POST"])  # noqa: F821
@login_required
async def sequence2txt():
    req = await request.form
    stream_mode = req.get("stream", "false").lower() == "true"
    files = await request.files
    if "file" not in files:
        return get_data_error_result(message="Missing 'file' in multipart form-data")

    uploaded = files["file"]

    ALLOWED_EXTS = {
        ".wav", ".mp3", ".m4a", ".aac",
        ".flac", ".ogg", ".webm",
        ".opus", ".wma"
    }

    filename = uploaded.filename or ""
    suffix = os.path.splitext(filename)[-1].lower()
    if suffix not in ALLOWED_EXTS:
        return get_data_error_result(message=
            f"Unsupported audio format: {suffix}. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTS))}"
        )
    fd, temp_audio_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    await uploaded.save(temp_audio_path)

    tenants = TenantService.get_info_by(current_user.id)
    if not tenants:
        return get_data_error_result(message="Tenant not found!")

    asr_id = tenants[0]["asr_id"]
    if not asr_id:
        return get_data_error_result(message="No default ASR model is set")

    asr_mdl=LLMBundle(tenants[0]["tenant_id"], LLMType.SPEECH2TEXT, asr_id)
    if not stream_mode:
        text = asr_mdl.transcription(temp_audio_path)
        try:
            os.remove(temp_audio_path)
        except Exception as e:
            logging.error(f"Failed to remove temp audio file: {str(e)}")
        return get_json_result(data={"text": text})
    async def event_stream():
        try:
            for evt in asr_mdl.stream_transcription(temp_audio_path):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:
            err = {"event": "error", "text": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
        finally:
            try:
                os.remove(temp_audio_path)
            except Exception as e:
                logging.error(f"Failed to remove temp audio file: {str(e)}")

    return Response(event_stream(), content_type="text/event-stream")

@manager.route("/tts", methods=["POST"])  # noqa: F821
@login_required
async def tts():
    req = await get_request_json()
    text = req["text"]
    
    # 检查是否提供了conversation_id，如果是，则尝试获取已存在的TTS文件
    conversation_id = req.get("conversation_id")
    if conversation_id:
        try:
            # 验证对话是否存在
            e, conv = ConversationService.get_by_id(conversation_id)
            if e:
                conv_data = conv.to_dict()
                tts_file_url = conv_data.get("tts_file_url")
                tts_status = conv_data.get("tts_status")
                
                # 如果TTS已生成且状态为completed，则直接返回已存储的音频文件
                if tts_file_url and tts_status == "completed":
                    # 解析URL获取文件路径
                    import urllib.parse
                    import re
                    parsed_url = urllib.parse.urlparse(tts_file_url)
                    path = parsed_url.path
                    # 提取文件名（假设路径格式为/bucket/tts/filename.mp3）
                    filename = path.split("/")[-1]
                    location = f"tts/{filename}"
                    
                    # 从MinIO获取文件，使用 conversation_id 作为 bucket
                    bucket = conversation_id
                    try:
                        blob = await asyncio.to_thread(settings.STORAGE_IMPL.get, bucket, location)
                        if blob:
                            # 返回音频文件
                            response = await make_response(blob)
                            ext = re.search(r"\.([^.]+)$", filename)
                            if ext:
                                response.headers.set('Content-Type', 'audio/%s' % ext.group(1))
                            response.headers.add_header("Cache-Control", "no-cache")
                            response.headers.add_header("Connection", "keep-alive")
                            response.headers.add_header("X-Accel-Buffering", "no")
                            return response
                    except Exception as e:
                        # 如果获取已存储文件失败，记录错误并回退到原始逻辑
                        logging.warning(f"Failed to get stored TTS file: {str(e)}")
                        pass

        except Exception as e:
            # 如果有任何错误，记录错误并回退到原始逻辑
            logging.warning(f"Error checking stored TTS file: {str(e)}")
            pass

    # 检查租户是否设置了TTS模型
    tenants = TenantService.get_info_by(current_user.id)
    if not tenants:
        return get_data_error_result(message="Tenant not found!")

    tts_id = tenants[0]["tts_id"]
    if not tts_id:
        # 如果没有设置TTS模型，但提供了conversation_id且有已存储的文件，可以尝试从消息中查找
        if conversation_id:
            try:
                e, conv = ConversationService.get_by_id(conversation_id)
                if e:
                    conv_data = conv.to_dict()
                    # 检查消息中是否有单独的tts_file_url
                    for msg in conv_data.get("message", []):
                        msg_tts_file_url = msg.get("tts_file_url")
                        msg_tts_status = msg.get("tts_status")
                        if msg_tts_file_url and msg_tts_status == "completed":
                            # 解析URL获取文件路径
                            import urllib.parse
                            import re
                            parsed_url = urllib.parse.urlparse(msg_tts_file_url)
                            path = parsed_url.path
                            # 提取文件名
                            filename = path.split("/")[-1]
                            location = f"tts/{filename}"
                            
                            # 从MinIO获取文件
                            bucket = conversation_id
                            try:
                                blob = await asyncio.to_thread(settings.STORAGE_IMPL.get, bucket, location)
                                if blob:
                                    # 返回音频文件
                                    response = await make_response(blob)
                                    ext = re.search(r"\.([^.]+)$", filename)
                                    if ext:
                                        response.headers.set('Content-Type', 'audio/%s' % ext.group(1))
                                    response.headers.add_header("Cache-Control", "no-cache")
                                    response.headers.add_header("Connection", "keep-alive")
                                    response.headers.add_header("X-Accel-Buffering", "no")
                                    return response
                            except Exception:
                                pass
            except Exception:
                pass
        
        # 如果没有找到已存储的文件，则返回错误
        return get_data_error_result(message="No default TTS model is set")

    tts_mdl = LLMBundle(tenants[0]["tenant_id"], LLMType.TTS, tts_id)

    def stream_audio():
        try:
            for txt in re.split(r"[，。/《》？；：！\n\r:;]+", text):
                for chunk in tts_mdl.tts(txt):
                    yield chunk
        except Exception as e:
            yield ("data:" + json.dumps({"code": 500, "message": str(e), "data": {"answer": "**ERROR**: " + str(e)}}, ensure_ascii=False)).encode("utf-8")

    resp = Response(stream_audio(), mimetype="audio/mpeg")
    resp.headers.add_header("Cache-Control", "no-cache")
    resp.headers.add_header("Connection", "keep-alive")
    resp.headers.add_header("X-Accel-Buffering", "no")

    return resp


@manager.route("/delete_msg", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "message_id")
async def delete_msg():
    req = await get_request_json()
    e, conv = ConversationService.get_by_id(req["conversation_id"])
    if not e:
        return get_data_error_result(message="Conversation not found!")

    conv = conv.to_dict()
    for i, msg in enumerate(conv["message"]):
        if req["message_id"] != msg.get("id", ""):
            continue
        assert conv["message"][i + 1]["id"] == req["message_id"]
        conv["message"].pop(i)
        conv["message"].pop(i)
        conv["reference"].pop(max(0, i // 2 - 1))
        break

    ConversationService.update_by_id(conv["id"], conv)
    return get_json_result(data=conv)


@manager.route("/thumbup", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "message_id")
async def thumbup():
    req = await get_request_json()
    e, conv = ConversationService.get_by_id(req["conversation_id"])
    if not e:
        return get_data_error_result(message="Conversation not found!")
    up_down = req.get("thumbup")
    feedback = req.get("feedback", "")
    conv = conv.to_dict()
    for i, msg in enumerate(conv["message"]):
        if req["message_id"] == msg.get("id", "") and msg.get("role", "") == "assistant":
            if up_down:
                msg["thumbup"] = True
                if "feedback" in msg:
                    del msg["feedback"]
            else:
                msg["thumbup"] = False
                if feedback:
                    msg["feedback"] = feedback
            break

    ConversationService.update_by_id(conv["id"], conv)
    return get_json_result(data=conv)


@manager.route("/ask", methods=["POST"])  # noqa: F821
@login_required
@validate_request("question", "kb_ids")
async def ask_about():
    req = await get_request_json()
    uid = current_user.id

    search_id = req.get("search_id", "")
    search_app = None
    search_config = {}
    if search_id:
        search_app = SearchService.get_detail(search_id)
    if search_app:
        search_config = search_app.get("search_config", {})

    async def stream():
        nonlocal req, uid
        try:
            async for ans in async_ask(req["question"], req["kb_ids"], uid, search_config=search_config):
                yield "data:" + json.dumps({"code": 0, "message": "", "data": ans}, ensure_ascii=False) + "\n\n"
        except Exception as e:
            yield "data:" + json.dumps({"code": 500, "message": str(e), "data": {"answer": "**ERROR**: " + str(e), "reference": []}}, ensure_ascii=False) + "\n\n"
        yield "data:" + json.dumps({"code": 0, "message": "", "data": True}, ensure_ascii=False) + "\n\n"

    resp = Response(stream(), mimetype="text/event-stream")
    resp.headers.add_header("Cache-control", "no-cache")
    resp.headers.add_header("Connection", "keep-alive")
    resp.headers.add_header("X-Accel-Buffering", "no")
    resp.headers.add_header("Content-Type", "text/event-stream; charset=utf-8")
    return resp


@manager.route("/mindmap", methods=["POST"])  # noqa: F821
@login_required
@validate_request("question", "kb_ids")
async def mindmap():
    req = await get_request_json()
    search_id = req.get("search_id", "")
    search_app = SearchService.get_detail(search_id) if search_id else {}
    search_config = search_app.get("search_config", {}) if search_app else {}
    kb_ids = search_config.get("kb_ids", [])
    kb_ids.extend(req["kb_ids"])
    kb_ids = list(set(kb_ids))

    mind_map = await gen_mindmap(req["question"], kb_ids, search_app.get("tenant_id", current_user.id), search_config)
    if "error" in mind_map:
        return server_error_response(Exception(mind_map["error"]))
    return get_json_result(data=mind_map)


@manager.route("/related_questions", methods=["POST"])  # noqa: F821
@login_required
@validate_request("question")
async def related_questions():
    req = await get_request_json()

    search_id = req.get("search_id", "")
    search_config = {}
    if search_id:
        if search_app := SearchService.get_detail(search_id):
            search_config = search_app.get("search_config", {})

    question = req["question"]

    chat_id = search_config.get("chat_id", "")
    chat_mdl = LLMBundle(current_user.id, LLMType.CHAT, chat_id)

    gen_conf = search_config.get("llm_setting", {"temperature": 0.9})
    if "parameter" in gen_conf:
        del gen_conf["parameter"]
    prompt = load_prompt("related_question")
    ans = await chat_mdl.async_chat(
        prompt,
        [
            {
                "role": "user",
                "content": f"""
Keywords: {question}
Related search terms:
    """,
            }
        ],
        gen_conf,
    )
    return get_json_result(data=[re.sub(r"^[0-9]\. ", "", a) for a in ans.split("\n") if re.match(r"^[0-9]\. ", a)])


@manager.route("/tts/generate", methods=["POST"])  # noqa: F821
@login_required
@validate_request("conversation_id", "content")
async def generate_tts():
    req = await get_request_json()
    conversation_id = req["conversation_id"]
    content = req["content"]

    try:
        # 验证对话是否存在
        e, conv = ConversationService.get_by_id(conversation_id)
        if not e:
            return get_data_error_result(message="Conversation not found!")

        # 记录日志
        logging.info(f"TTS generate request: conversation_id={conversation_id}, content={content}, type={type(content)}")

        # 确保content是字符串
        if not isinstance(content, str):
            content = str(content)
            logging.info(f"Converted content to string: {content}")

        # 调用Chatterbox TTS API
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 构建表单数据
            form_data = {
                "text": content,
                "language_id": "zh",  # 默认中文
                "exaggeration": "0.5",
                "temperature": "0.8",
                "cfg_weight": "0.5",
                "seed_num": "0",
                "callback_url": CALLBACK_URL
            }
            logging.info(f"TTS API form data: {form_data}")
            
            # 使用multipart/form-data格式发送请求
            tts_response = await client.post(
                TTS_API_URL,
                data=form_data
            )

            logging.info(f"TTS API response status: {tts_response.status_code}")
            logging.info(f"TTS API response text: {tts_response.text}")
            
            if tts_response.status_code != 200:
                logging.error(f"TTS API error: {tts_response.text}")
                return get_data_error_result(message=f"TTS API error: {tts_response.text}")

            tts_data = tts_response.json()
            logging.info(f"TTS API response json: {tts_data}")
            
            if tts_data.get("code") != 0:
                logging.error(f"TTS API error: {tts_data.get('msg')}")
                return get_data_error_result(message=f"TTS API error: {tts_data.get('msg')}")

            task_id = tts_data.get("task_id")
            if not task_id:
                return get_data_error_result(message="Invalid TTS API response: missing task_id")

            # 更新对话的tts_task_id
            conv_data = conv.to_dict()
            conv_data["tts_task_id"] = task_id
            conv_data["tts_status"] = "pending"
            ConversationService.update_by_id(conversation_id, conv_data)

            return get_json_result(data={"task_id": task_id})

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)


@manager.route("/tts/callback", methods=["POST"])  # noqa: F821
async def tts_callback():
    """处理TTS回调"""
    try:
        req = await get_request_json()
        task_id = req.get("task_id")
        status = req.get("status")
        audio_url = req.get("result", {}).get("output_url")

        if not task_id:
            return get_data_error_result(message="Missing task_id")

        logging.info(f"Received TTS callback: task_id={task_id}, status={status}")

        # 首先根据task_id查找对话（对话级别的tts_task_id）
        convs = ConversationService.query(tts_task_id=task_id)
        if not convs:
            # 如果在对话级别没找到，则遍历所有对话查找消息级别的tts_task_id
            logging.info(f"No conversation found with conversation-level tts_task_id={task_id}, searching in messages...")
            
            # 获取所有属于当前租户的对话（这里需要更精确的查询）
            # 由于我们不知道具体是哪个对话，需要更通用的方法
            # 我们先尝试通过数据库直接查询
            from api.db.db_models import Conversation as ConversationModel
            # 查找消息中包含该tts_task_id的对话
            matched_conv = None
            # 这里我们需要遍历所有对话，查找包含指定tts_task_id的消息
            # 为了效率，我们直接查询数据库
            for conv_record in ConversationModel.select():
                try:
                    conv_dict = conv_record.to_dict()
                    messages = conv_dict.get("message", [])
                    for msg in messages:
                        if msg.get("tts_task_id") == task_id or msg.get("ttsTaskId") == task_id:
                            matched_conv = conv_record
                            logging.info(f"Found conversation {conv_record.id} with message containing tts_task_id={task_id}")
                            break
                    if matched_conv:
                        break
                except Exception as e:
                    logging.warning(f"Error processing conversation {conv_record.id}: {str(e)}")
                    continue
            
            if matched_conv:
                convs = [matched_conv]
            else:
                logging.warning(f"No conversation found for task_id: {task_id}")
                return get_data_error_result(message="Conversation not found for task_id")

        if not convs:
            return get_data_error_result(message="Conversation not found for task_id")

        conv = convs[0]
        conv_data = conv.to_dict()
        old_status = conv_data.get("tts_status", "unknown")
        conv_data["tts_status"] = status

        # 查找并更新消息级别的TTS状态
        updated_messages = False
        for msg in conv_data.get("message", []):
            # 检查消息级别是否有tts_task_id匹配（兼容不同字段名）
            if msg.get("tts_task_id") == task_id or msg.get("ttsTaskId") == task_id:
                old_msg_status = msg.get("tts_status", "unknown")
                msg["tts_status"] = status
                if status == "completed":
                    # 如果有可用的音频URL，也更新到消息级别
                    if audio_url:
                        msg["tts_file_url"] = audio_url
                updated_messages = True
                logging.info(f"Updated message-level TTS status for message {msg.get('id', 'unknown')}: from {old_msg_status} to {status}")

        if status == "completed":
            logging.info(f"TTS task completed for task_id: {task_id}, processing audio download...")
            # 使用task_id下载TTS文件
            try:
                # 使用task_id从TTS服务下载文件
                tts_download_url = f"http://127.0.0.1:8001/download_tts_audio?task_id={task_id}"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    audio_response = await client.get(tts_download_url)
                    if audio_response.status_code != 200:
                        logging.error(f"Failed to download audio file: {audio_response.status_code}, response: {audio_response.text}")
                        # 即使下载失败也更新状态，但记录错误
                        success = ConversationService.update_by_id(conv.id, conv_data)
                        if success:
                            logging.info(f"TTS status updated to completed (without file) for conversation {conv.id}, task_id {task_id}")
                            return get_json_result(data={"success": True, "message": "Status updated but audio download failed"})
                        else:
                            logging.error(f"Failed to update conversation {conv.id} with TTS status")
                            return get_data_error_result(message="Failed to update conversation")
                    
                    audio_data = audio_response.content
                    logging.info(f"Successfully downloaded audio data ({len(audio_data)} bytes) for task_id: {task_id}")

                # 生成唯一的文件名和位置
                import uuid
                filename = f"{task_id}_{uuid.uuid4().hex}.mp3"
                location = f"tts/{filename}"

                # 上传到MinIO，参考 /v1/file/upload 的实现
                # 使用 conversation_id 作为 bucket
                bucket = conv.id
                await asyncio.to_thread(settings.STORAGE_IMPL.put, bucket, location, audio_data)
                logging.info(f"Audio file uploaded to MinIO: {bucket}/{location}")

                # 获取预签名URL
                presigned_url = await asyncio.to_thread(
                    minio_client.get_presigned_url, bucket, location, expires=timedelta(days=7)
                )
                
                # 更新对话级别的URL
                conv_data["tts_file_url"] = presigned_url
                logging.info(f"TTS file uploaded to MinIO: {bucket}/{location}, URL: {presigned_url}")
                
                # 同时更新对应消息的URL（如果之前没更新的话）
                if not updated_messages:  # 如果还没有更新消息级别，尝试根据task_id查找
                    for msg in conv_data.get("message", []):
                        if msg.get("tts_task_id") == task_id or msg.get("ttsTaskId") == task_id:
                            msg["tts_file_url"] = presigned_url
                            updated_messages = True
                            logging.info(f"Updated message-level TTS file URL for message {msg.get('id', 'unknown')}")
            except Exception as e:
                logging.exception(f"Error in TTS audio processing for task_id {task_id}: {str(e)}")
                # 出错时仍更新状态，但不设置文件URL
                pass

        # 更新对话记录
        success = ConversationService.update_by_id(conv.id, conv_data)
        if not success:
            logging.error(f"Failed to update conversation {conv.id} with TTS status")
            return get_data_error_result(message="Failed to update conversation")

        # 记录成功日志
        logging.info(f"TTS callback processed successfully: task_id={task_id}, old_status={old_status}, new_status={status}, conv_id={conv.id}, has_file_url={bool(conv_data.get('tts_file_url'))}, messages_updated={updated_messages}")
        return get_json_result(data={"success": True})

    except Exception as e:
        logging.exception(f"Error in TTS callback handler: {str(e)}")
        return server_error_response(e)


@manager.route("/tts/down", methods=["GET"])  # noqa: F821
@login_required
async def download_tts():
    """下载合成的语音文件，参考 /v1/file/get 的实现"""
    conversation_id = request.args.get("conversation_id")
    if not conversation_id:
        return get_data_error_result(message="Missing conversation_id")

    try:
        # 验证对话是否存在
        e, conv = ConversationService.get_by_id(conversation_id)
        if not e:
            return get_data_error_result(message="Conversation not found!")

        # 检查是否有tts_file_url
        conv_data = conv.to_dict()
        tts_file_url = conv_data.get("tts_file_url")
        tts_status = conv_data.get("tts_status")

        if not tts_file_url:
            return get_data_error_result(message="No TTS audio file available")

        if tts_status != "completed":
            return get_data_error_result(message="TTS task is not completed")

        # 从minio下载文件，参考 /v1/file/get 的实现
        # 解析tts_file_url获取文件路径
        import urllib.parse
        import re
        parsed_url = urllib.parse.urlparse(tts_file_url)
        path = parsed_url.path
        # 提取文件名（假设路径格式为/bucket/tts/filename.mp3）
        filename = path.split("/")[-1]
        location = f"tts/{filename}"

        # 从minio获取文件，使用 conversation_id 作为 bucket
        bucket = conversation_id
        try:
            # 下载文件内容，参考 /v1/file/get 的实现
            blob = await asyncio.to_thread(settings.STORAGE_IMPL.get, bucket, location)
            if not blob:
                return get_data_error_result(message="Failed to download audio file from MinIO")
        except Exception as e:
            logging.exception(e)
            return get_data_error_result(message="Failed to download audio file from MinIO")

        # 返回音频文件，参考 /v1/file/get 的实现
        response = await make_response(blob)
        ext = re.search(r"\.([^.]+)$", filename)
        if ext:
            response.headers.set('Content-Type', 'audio/%s' % ext.group(1))
        response.headers.set('Content-Disposition', f'attachment; filename="{filename}"')
        return response

    except Exception as e:
        logging.exception(e)
        return server_error_response(e)
