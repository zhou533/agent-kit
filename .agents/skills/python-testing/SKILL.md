---
name: python-testing
description: Python 测试策略，基于 pytest 与 TDD 方法论，涵盖 fixture、mocking、参数化与覆盖率要求。
origin: AAN
---

# Python 测试模式

一套完整的 Python 测试策略，基于 pytest、TDD 方法论与最佳实践。

## 何时激活

- 编写新的 Python 代码（遵循 TDD：red、green、refactor）
- 为 Python 项目设计测试套件
- 审查 Python 测试覆盖率
- 搭建测试基础设施

## 核心测试哲学

### 测试驱动开发（TDD）

始终遵循 TDD 循环：

1. **RED**：为预期行为写一个失败的测试
2. **GREEN**：写最少的代码让测试通过
3. **REFACTOR**：在保持测试绿色的前提下改进代码

```python
# Step 1: 写失败的测试（RED）
def test_add_numbers():
    result = add(2, 3)
    assert result == 5

# Step 2: 写最少实现（GREEN）
def add(a, b):
    return a + b

# Step 3: 按需重构（REFACTOR）
```

### 覆盖率要求

- **目标**：80%+ 代码覆盖率
- **关键路径**：必须 100% 覆盖
- 使用 `pytest --cov` 测量覆盖率

```bash
pytest --cov=mypackage --cov-report=term-missing --cov-report=html
```

## pytest 基础

### 基础测试结构

```python
import pytest

def test_addition():
    """Test basic addition."""
    assert 2 + 2 == 4

def test_string_uppercase():
    """Test string uppercasing."""
    text = "hello"
    assert text.upper() == "HELLO"

def test_list_append():
    """Test list append."""
    items = [1, 2, 3]
    items.append(4)
    assert 4 in items
    assert len(items) == 4
```

### 断言

```python
# 相等
assert result == expected

# 不等
assert result != unexpected

# 真值判断
assert result  # Truthy
assert not result  # Falsy
assert result is True  # 精确等于 True
assert result is False  # 精确等于 False
assert result is None  # 精确等于 None

# 成员关系
assert item in collection
assert item not in collection

# 比较
assert result > 0
assert 0 <= result <= 100

# 类型检查
assert isinstance(result, str)

# 异常测试（推荐写法）
with pytest.raises(ValueError):
    raise ValueError("error message")

# 检查异常消息
with pytest.raises(ValueError, match="invalid input"):
    raise ValueError("invalid input provided")

# 检查异常属性
with pytest.raises(ValueError) as exc_info:
    raise ValueError("error message")
assert str(exc_info.value) == "error message"
```

## Fixtures

### 基础用法

```python
import pytest

@pytest.fixture
def sample_data():
    """提供样本数据的 fixture。"""
    return {"name": "Alice", "age": 30}

def test_sample_data(sample_data):
    """使用 fixture 的测试。"""
    assert sample_data["name"] == "Alice"
    assert sample_data["age"] == 30
```

### 带 setup / teardown 的 Fixture

```python
@pytest.fixture
def database():
    """带 setup 与 teardown 的 fixture。"""
    # Setup
    db = Database(":memory:")
    db.create_tables()
    db.insert_test_data()

    yield db  # 提供给测试

    # Teardown
    db.close()

def test_database_query(database):
    """测试数据库操作。"""
    result = database.query("SELECT * FROM users")
    assert len(result) > 0
```

### Fixture 作用域

```python
# 函数作用域（默认）—— 每个测试都会运行
@pytest.fixture
def temp_file():
    with open("temp.txt", "w") as f:
        yield f
    os.remove("temp.txt")

# 模块作用域 —— 每个模块只运行一次
@pytest.fixture(scope="module")
def module_db():
    db = Database(":memory:")
    db.create_tables()
    yield db
    db.close()

# 会话作用域 —— 整个测试会话只运行一次
@pytest.fixture(scope="session")
def shared_resource():
    resource = ExpensiveResource()
    yield resource
    resource.cleanup()
```

### 带参数的 Fixture

```python
@pytest.fixture(params=[1, 2, 3])
def number(request):
    """参数化 fixture。"""
    return request.param

def test_numbers(number):
    """测试会运行 3 次，每次一个参数。"""
    assert number > 0
```

### 组合使用多个 Fixture

```python
@pytest.fixture
def user():
    return User(id=1, name="Alice")

@pytest.fixture
def admin():
    return User(id=2, name="Admin", role="admin")

def test_user_admin_interaction(user, admin):
    """同时使用多个 fixture。"""
    assert admin.can_manage(user)
```

### Autouse Fixtures

```python
@pytest.fixture(autouse=True)
def reset_config():
    """每个测试前自动运行。"""
    Config.reset()
    yield
    Config.cleanup()

def test_without_fixture_call():
    # reset_config 会自动运行
    assert Config.get_setting("debug") is False
```

### 用 conftest.py 共享 Fixture

```python
# tests/conftest.py
import pytest

@pytest.fixture
def client():
    """所有测试共享的 fixture。"""
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_headers(client):
    """为 API 测试生成鉴权 headers。"""
    response = client.post("/api/login", json={
        "username": "test",
        "password": "test"
    })
    token = response.json["token"]
    return {"Authorization": f"Bearer {token}"}
```

## 参数化

### 基础参数化

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("PyThOn", "PYTHON"),
])
def test_uppercase(input, expected):
    """测试会用不同输入运行 3 次。"""
    assert input.upper() == expected
```

### 多参数

```python
@pytest.mark.parametrize("a,b,expected", [
    (2, 3, 5),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_add(a, b, expected):
    """用多组输入测试加法。"""
    assert add(a, b) == expected
```

### 带可读 ID 的参数化

```python
@pytest.mark.parametrize("input,expected", [
    ("valid@email.com", True),
    ("invalid", False),
    ("@no-domain.com", False),
], ids=["valid-email", "missing-at", "missing-domain"])
def test_email_validation(input, expected):
    """带可读测试 ID 的邮箱校验测试。"""
    assert is_valid_email(input) is expected
```

### 参数化 Fixture

```python
@pytest.fixture(params=["sqlite", "postgresql", "mysql"])
def db(request):
    """对多种数据库后端测试。"""
    if request.param == "sqlite":
        return Database(":memory:")
    elif request.param == "postgresql":
        return Database("postgresql://localhost/test")
    elif request.param == "mysql":
        return Database("mysql://localhost/test")

def test_database_operations(db):
    """测试会对每种数据库各跑一次。"""
    result = db.query("SELECT 1")
    assert result is not None
```

## 标记与测试选取

### 自定义标记

```python
# 标记慢测试
@pytest.mark.slow
def test_slow_operation():
    time.sleep(5)

# 标记集成测试
@pytest.mark.integration
def test_api_integration():
    response = requests.get("https://api.example.com")
    assert response.status_code == 200

# 标记单元测试
@pytest.mark.unit
def test_unit_logic():
    assert calculate(2, 3) == 5
```

### 选取特定测试

```bash
# 只跑快测试
pytest -m "not slow"

# 只跑集成测试
pytest -m integration

# 集成或慢测试
pytest -m "integration or slow"

# 是 unit 但不是 slow 的
pytest -m "unit and not slow"
```

### 在 pytest.ini 注册标记

```ini
[pytest]
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    django: marks tests as requiring Django
```

## Mock 与 Patch

### Mock 函数

```python
from unittest.mock import patch, Mock

@patch("mypackage.external_api_call")
def test_with_mock(api_call_mock):
    """用 mock 替换外部 API。"""
    api_call_mock.return_value = {"status": "success"}

    result = my_function()

    api_call_mock.assert_called_once()
    assert result["status"] == "success"
```

### Mock 返回值

```python
@patch("mypackage.Database.connect")
def test_database_connection(connect_mock):
    """用 mock 替换数据库连接。"""
    connect_mock.return_value = MockConnection()

    db = Database()
    db.connect()

    connect_mock.assert_called_once_with("localhost")
```

### Mock 异常

```python
@patch("mypackage.api_call")
def test_api_error_handling(api_call_mock):
    """用 mock 注入异常做错误处理测试。"""
    api_call_mock.side_effect = ConnectionError("Network error")

    with pytest.raises(ConnectionError):
        api_call()

    api_call_mock.assert_called_once()
```

### Mock 上下文管理器

```python
@patch("builtins.open", new_callable=mock_open)
def test_file_reading(mock_file):
    """用 mock 替换 open 读取文件。"""
    mock_file.return_value.read.return_value = "file content"

    result = read_file("test.txt")

    mock_file.assert_called_once_with("test.txt", "r")
    assert result == "file content"
```

### 使用 Autospec

```python
@patch("mypackage.DBConnection", autospec=True)
def test_autospec(db_mock):
    """用 autospec 捕获 API 误用。"""
    db = db_mock.return_value
    db.query("SELECT * FROM users")

    # 如果 DBConnection 没有 query 方法，这里会报错
    db_mock.assert_called_once()
```

### Mock 类实例

```python
class TestUserService:
    @patch("mypackage.UserRepository")
    def test_create_user(self, repo_mock):
        """用 mock repository 测试用户创建。"""
        repo_mock.return_value.save.return_value = User(id=1, name="Alice")

        service = UserService(repo_mock.return_value)
        user = service.create_user(name="Alice")

        assert user.name == "Alice"
        repo_mock.return_value.save.assert_called_once()
```

### Mock Property

```python
@pytest.fixture
def mock_config():
    """创建带 property 的 mock。"""
    config = Mock()
    type(config).debug = PropertyMock(return_value=True)
    type(config).api_key = PropertyMock(return_value="test-key")
    return config

def test_with_mock_config(mock_config):
    """用带 property 的 mock config 测试。"""
    assert mock_config.debug is True
    assert mock_config.api_key == "test-key"
```

## 异步代码测试

### pytest-asyncio 下的异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数。"""
    result = await async_add(2, 3)
    assert result == 5

@pytest.mark.asyncio
async def test_async_with_fixture(async_client):
    """测试异步函数 + 异步 fixture。"""
    response = await async_client.get("/api/users")
    assert response.status_code == 200
```

### 异步 Fixture

```python
@pytest.fixture
async def async_client():
    """提供异步测试客户端的异步 fixture。"""
    app = create_app()
    async with app.test_client() as client:
        yield client

@pytest.mark.asyncio
async def test_api_endpoint(async_client):
    """使用异步 fixture 的测试。"""
    response = await async_client.get("/api/data")
    assert response.status_code == 200
```

### Mock 异步函数

```python
@pytest.mark.asyncio
@patch("mypackage.async_api_call")
async def test_async_mock(api_call_mock):
    """异步函数 + mock。"""
    api_call_mock.return_value = {"status": "ok"}

    result = await my_async_function()

    api_call_mock.assert_awaited_once()
    assert result["status"] == "ok"
```

## 异常测试

### 测试预期异常

```python
def test_divide_by_zero():
    """测试除零抛出 ZeroDivisionError。"""
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_custom_exception():
    """测试自定义异常及其消息。"""
    with pytest.raises(ValueError, match="invalid input"):
        validate_input("invalid")
```

### 测试异常属性

```python
def test_exception_with_details():
    """测试带自定义属性的异常。"""
    with pytest.raises(CustomError) as exc_info:
        raise CustomError("error", code=400)

    assert exc_info.value.code == 400
    assert "error" in str(exc_info.value)
```

## 副作用测试

### 测试文件操作

```python
import tempfile
import os

def test_file_processing():
    """用临时文件测试文件处理。"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("test content")
        temp_path = f.name

    try:
        result = process_file(temp_path)
        assert result == "processed: test content"
    finally:
        os.unlink(temp_path)
```

### 使用 pytest 内置 tmp_path Fixture

```python
def test_with_tmp_path(tmp_path):
    """使用 pytest 内置的临时路径 fixture。"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    result = process_file(str(test_file))
    assert result == "hello world"
    # tmp_path 会自动清理
```

### 使用 tmpdir Fixture

```python
def test_with_tmpdir(tmpdir):
    """使用 pytest 的 tmpdir fixture。"""
    test_file = tmpdir.join("test.txt")
    test_file.write("data")

    result = process_file(str(test_file))
    assert result == "data"
```

## 测试组织

### 目录结构

```
tests/
├── conftest.py                 # 共享 fixture
├── __init__.py
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_services.py
├── integration/                # 集成测试
│   ├── __init__.py
│   ├── test_api.py
│   └── test_database.py
└── e2e/                        # 端到端测试
    ├── __init__.py
    └── test_user_flow.py
```

### 测试类

```python
class TestUserService:
    """用类分组相关测试。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前自动运行。"""
        self.service = UserService()

    def test_create_user(self):
        """测试用户创建。"""
        user = self.service.create_user("Alice")
        assert user.name == "Alice"

    def test_delete_user(self):
        """测试用户删除。"""
        user = User(id=1, name="Bob")
        self.service.delete_user(user)
        assert not self.service.user_exists(1)
```

## 最佳实践

### DO

- **遵循 TDD**：先写测试再写代码（red-green-refactor）
- **一次只测一件事**：每个测试只验证一个行为
- **描述性命名**：`test_user_login_with_invalid_credentials_fails`
- **使用 fixture**：用 fixture 消除重复
- **mock 外部依赖**：不要依赖外部服务
- **覆盖边界情形**：空输入、None、边界值
- **目标 80%+ 覆盖率**：优先覆盖关键路径
- **保持测试快速**：用 marker 分离慢测试

### DON'T

- **不要测实现**：测行为而不是内部细节
- **不要在测试中写复杂条件**：保持测试简单
- **不要忽略失败**：所有测试都必须通过
- **不要测三方库代码**：相信它们自己会正常工作
- **不要跨测试共享状态**：测试应彼此独立
- **不要在测试里 catch 异常**：用 `pytest.raises`
- **不要用 print**：用断言和 pytest 输出
- **不要写过脆弱的测试**：避免过于具体的 mock

## 常见模式

### 测试 API Endpoint（FastAPI / Flask）

```python
@pytest.fixture
def client():
    app = create_app(testing=True)
    return app.test_client()

def test_get_user(client):
    response = client.get("/api/users/1")
    assert response.status_code == 200
    assert response.json["id"] == 1

def test_create_user(client):
    response = client.post("/api/users", json={
        "name": "Alice",
        "email": "alice@example.com"
    })
    assert response.status_code == 201
    assert response.json["name"] == "Alice"
```

### 测试数据库操作

```python
@pytest.fixture
def db_session():
    """创建测试数据库 session。"""
    session = Session(bind=engine)
    session.begin_nested()
    yield session
    session.rollback()
    session.close()

def test_create_user(db_session):
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    db_session.commit()

    retrieved = db_session.query(User).filter_by(name="Alice").first()
    assert retrieved.email == "alice@example.com"
```

### 测试类方法

```python
class TestCalculator:
    @pytest.fixture
    def calculator(self):
        return Calculator()

    def test_add(self, calculator):
        assert calculator.add(2, 3) == 5

    def test_divide_by_zero(self, calculator):
        with pytest.raises(ZeroDivisionError):
            calculator.divide(10, 0)
```

## pytest 配置

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --disable-warnings
    --cov=mypackage
    --cov-report=term-missing
    --cov-report=html
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--cov=mypackage",
    "--cov-report=term-missing",
    "--cov-report=html",
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_utils.py

# 运行特定测试
pytest tests/test_utils.py::test_function

# 详细输出
pytest -v

# 带覆盖率运行
pytest --cov=mypackage --cov-report=html

# 只跑快测试
pytest -m "not slow"

# 首次失败即停
pytest -x

# N 次失败后停止
pytest --maxfail=3

# 只重跑上次失败的
pytest --lf

# 按模式匹配运行
pytest -k "test_user"

# 失败时进入调试器
pytest --pdb
```

## 速查

| 模式 | 用法 |
|------|------|
| `pytest.raises()` | 测试预期异常 |
| `@pytest.fixture()` | 创建可复用 fixture |
| `@pytest.mark.parametrize()` | 多输入运行 |
| `@pytest.mark.slow` | 标记慢测试 |
| `pytest -m "not slow"` | 跳过慢测试 |
| `@patch()` | mock 函数与类 |
| `tmp_path` fixture | 自动临时目录 |
| `pytest --cov` | 生成覆盖率报告 |
| `assert` | 简洁可读的断言 |

**请记住**：测试也是代码。保持整洁、可读、可维护。好测试捕获 bug；一流测试预防 bug。
