git clone https://github.com/infiniflow/ragflow.git

cd ragflow/docker
docker compose -f docker-compose.yml up -d

访问登录：
http://192.168.56.21/admin
用户名密码：
admin@ragflow.io
admin

新建：
test@ragflow.io
test123

普通用户：
http://192.168.56.21

处理问题：
C:\Users\Administrator\.ollama\config
config.json
嵌入模型：
ollama run deepseek-r1:32b
http://192.168.56.3:11434

ollama run mxbai-embed-large

本地启动前后端：
cd ragflow/
pip install uv pre-commit

# 设置环境变量
$env:PYTHONPATH = "$(Get-Location)"
$env:HF_ENDPOINT = "https://hf-mirror.com"
# 安装 Python 依赖
uv sync --python 3.12
uv run download_deps.py --china-mirrors
pre-commit install

# 激活虚拟环境
.venv\Scripts\activate  # Windows命令

# 启动服务
cd D:\workspace\PycharmProjects\ragflow
$env:PYTHONPATH = "$(Get-Location)"
python api/ragflow_server.py
访问：http://0.0.0.0:9380

#启动任务执行器
$env:PYTHONPATH = "$(Get-Location)"
python rag/svr/task_executor.py


# 前端
安装前端依赖：
cd web
npm install

cd web
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

LLM：


2.直接使用 Transformers API
本地falsk/fastapi


