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
.venv\Scripts\activate  # Windows 命令

# 启动服务
cd api
python ragflow_server.py
访问：http://0.0.0.0:9380
python task_executor.py


# 前端
安装前端依赖：
cd web
npm install

npm run dev

访问：
http://localhost:9222/
