===================================================== Linux Docker部署的服务 ===============================================================

git clone https://github.com/infiniflow/ragflow.git

cd ragflow/docker
docker compose -f docker-compose.yml up -d

访问登录：
http://192.168.56.21/admin
用户名密码：
admin@ragflow.io
admin

新建普通用户：
http://192.168.56.21
test@ragflow.io
test123


处理问题：
C:\Users\Administrator\.ollama\config
config.json
嵌入模型：
ollama run deepseek-r1:32b
http://192.168.56.3:11434

ollama run mxbai-embed-large

===================================================== Windows 本机测试部署服务 ===============================================================

本地启动前后端：
# 确保在ragflow或rag环境中 安装uv
pip install uv pre-commit
# 安装pre-commit
pre-commit install


# 前端
安装前端依赖：
cd web
npm install
npm run dev

访问：
http://localhost:9222/


---------------------------OCR 模型------------------------------------------------
https://opendatalab.github.io/MinerU/zh/usage/plugin/RagFlow/
本地安装MinerU
mineru-api --host 0.0.0.0 --port 8000

---------------------------Rerank 模型------------------------------------------------
# 1. 启动 Xinference 服务
docker run -d -p 9997:9997 --name xinference-server xprobe/xinference:latest
# 2. 注册模型
# 访问 http://localhost:9997
# 或使用命令行注册模型
xinference launch --model-name "bge-m3" --model-type embedding
xinference launch --model-name "bge-reranker-v2-m3" --model-type rerank
xinference launch --model-name "llava-v1.6-mistral-7b" --model-type llm


windows本地：
1.Xinference 托管 Hugging Face 模型
conda create -n xinference python=3.10
conda activate xinference
# 使用pip从官方源安装CUDA 12.1版本的PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install "xinference[all]"
xinference-local --host 127.0.0.1 --port 9997
访问：
http://127.0.0.1:9997






======================================================佳迪 RTX 409D 台式机部署的服务分布===============================================================
## ################################# 1.部署规划： ###################################
中间件： 虚拟机
ragflow服务： 虚拟机中（本地Conda Python虚拟环境） 和本地都有
LLM 部署在ollama
xinference 部署embedding模型 + Rerank模型
PDF OCR MinerU

-------------------------------------------
Ragflow 后端Python服务 + Task 执行服务（两个都要启动）
-------------------------------------------

本地后端
# 设置环境变量
$env:HF_ENDPOINT=“https://hf-mirror.com”
$env:UV_INDEX_URL=“https://mirrors.aliyun.com/pypi/simple/”

# 安装依赖
uv venv --python 3.12.4
uv sync --python 3.12.4
# 运行依赖下载
uv run python download_deps.py --china-mirrors

#新开一个终端窗口
$env:HF_ENDPOINT=“https://hf-mirror.com”
# 启动服务
.\.venv\Scripts\activate
python -m api.ragflow_server
访问：http://127.0.0.1:9380

新开一个终端窗口
#启动任务执行器
# 设置环境变量
$env:HF_ENDPOINT=“https://hf-mirror.com”
.\.venv\Scripts\activate
python -m rag.svr.task_executor

-------------------------------------------
Ragflow Node 前端服务
-------------------------------------------
本地 前端
cd web
npm install
npm run dev

访问：
http://127.0.0.1:9222/

-------------------------------------------
Ollama LLM/Chat
-------------------------------------------
1.3. 模型服务：
本地Ollama 部署LLM：
ollama deepseek-r1:32b

访问：
http://127.0.0.1:11434
-------------------------------------------
Xinference
-------------------------------------------
本地虚拟环境 Python xinference部署：
嵌入模型： xinference
Qwen3-Embedding-0.6B
Rerank模型：xinference
Qwen3-Reranker-0.6B

conda create -n xinference python=3.10
conda activate xinference
# 使用pip从官方源安装CUDA 12.1版本的PyTorch

# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
#    注意：每晚构建版更新快，通常支持最新的GPU架构
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129

pip install "xinference[all]" --index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
xinference-local --host 127.0.0.1 --port 9997

访问：
http://127.0.0.1:9997/
-------------------------------------------
MinerU
-------------------------------------------
PDF处理 MinerU Python MinerU虚拟环境：
MinerU处理

conda create -n MinerU python=3.10
conda activate MinerU

# 安装最新版本 PyTorch（支持最新 GPU 架构）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu129

pip install --upgrade pip
pip install uv --index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
uv pip install -U "mineru[all]"

# 设置环境变量强制使用 CPU
$env:CUDA_VISIBLE_DEVICES = "-1"
mineru-gradio --server-name 0.0.0.0 --server-port 7860

mineru-api --host 0.0.0.0 --port 8000

访问：
http://127.0.0.1:7860

API:
http://127.0.0.1:8000
-------------------------------------------
img2text/asr/tts
-------------------------------------------
图片模型 图片识别：暂不部署; 语音模型、TTS模型暂不部署

## ################################# 2.模型配置： ###################################
##### 2.模型配置： #####
1. Ollama 可选模型搜索 ollama 配置
http://127.0.0.1:11434

2. PDF、OCR 处理，搜索MinerU
http://127.0.0.1:8000

3. Embedding+Rerank xinference,搜索xinference 添加
http://127.0.0.1:9997/
嵌入模型： xinference
ID: Qwen3-Embedding-0.6B
Rerank模型：xinference
ID: Qwen3-Reranker-0.6B


## ################################# 3.重新启动： ###################################
1. 启动 virtualbox 虚拟机 192.168.56.21

2. 启动本都MinerU OCR： E:\ragflow\MinerU
conda activate MinerU
mineru-api --host 0.0.0.0 --port 8000

3.启动ragflow 后端服务（2个）：  E:\ragflow\ragflow
服务启动：
$env:HF_ENDPOINT=“https://hf-mirror.com”
# 启动服务
.\.venv\Scripts\activate
python -m api.ragflow_server
访问：http://127.0.0.1:9380

TASK启动（新的CMD窗口）：
新开一个终端窗口
$env:HF_ENDPOINT=“https://hf-mirror.com”
.\.venv\Scripts\activate
python -m rag.svr.task_executor

4.启动ragflow 前端服务：
cd web
npm install
npm run dev

5.xinference 服务启动：
conda activate xinference
xinference-local --host 127.0.0.1 --port 9997

需要手动启动：
嵌入模型： xinference
ID: Qwen3-Embedding-0.6B
Rerank模型：xinference
ID: Qwen3-Reranker-0.6B

## ################################# 4.访问测试  ###################################
访问登录：
http://127.0.0.1/admin
用户名密码：
admin@ragflow.io
admin


http://127.0.0.1
普通用户：
test@ragflow.io
test123




=================================================================================================
便捷使用
查看 uv 自身使用的 Python 版本：
uv run python --version

查看系统中安装的所有 Python 版本：
uv python list --all

查看 Python 安装目录： 
uv run which python
# 或者在 Windows 上
uv run where python

查看特定版本的 Python 安装路径：
uv python find 3.12.4

在 Python 环境中查看详细信息：
uv run python -c "import sys; print(sys.executable)"

