# 一品翠坊 · 项目规范

## 工作流规范

### 新任务必须先建分支
每次开始新任务，必须先从 `dev` 新建功能分支，完成后再合并，禁止直接在 `main` 或 `dev` 上提交功能代码。

```bash
# 标准流程
git checkout dev
git pull
git checkout -b feat/xxx   # 新建功能分支
# ... 写代码、提交 ...
git checkout dev
git merge feat/xxx         # 合并回 dev
# 分支保留，不删除
```

### 分支保留规则
功能或 bug 修复分支合并后**不删除**，保留完整开发历史。

### 分支命名
```
main        稳定版本，只接受来自 dev 的合并
dev         开发主分支
feat/xxx    新功能，如 feat/product-upload
fix/xxx     修复，如 fix/image-path
style/xxx   样式调整
refactor/xxx 重构
```

---

## Git Commit 规范

### 格式
```
<类型>(<范围>): <简短描述>
```

### 类型
| 类型 | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `style` | 样式调整，不影响逻辑 |
| `refactor` | 重构，不新增功能也不修复 bug |
| `docs` | 文档更新 |
| `chore` | 配置、依赖等杂项 |
| `test` | 测试相关 |

### Language rule
All commit messages **must be written in English** — subject line and body.

### Examples
```bash
feat(products): add product image upload
fix(auth): return 401 when JWT has expired
style(home): adjust hero section spacing
chore: add ESLint and Prettier config
```

---

## 代码规范

### 命名
```javascript
// 变量/函数：小驼峰
const productList = [];
function getProductById() {}

// 类：大驼峰
class ProductCard {}

// 常量：全大写下划线
const MAX_FILE_SIZE = 5 * 1024 * 1024;

// CSS 类名：小写短横线
// .product-card {}
// .hero-title {}
```

### 文件命名
```
组件：    ProductCard.js    大驼峰
JS工具：  product-utils.js  小写短横线
路由：    products.js       小写
```

### 函数原则
- 一个函数只做一件事
- 函数不超过 50 行
- 嵌套不超过 3 层，超过则拆函数

### Comment language rule
All inline comments and JSDoc **must be written in English**.

### Comment style
```javascript
// ✅ Explain "why", not "what"
// Gold price is calculated per gram, multiply by today's live rate
const price = goldPrice * weight;

/**
 * Fetch product list by category
 * @param {string} category - category key (gold / silver / jade)
 * @param {number} page - page number
 * @returns {Array} product list
 */
function getProducts(category, page) {}
```

### 文件规范
- 每个文件不超过 300 行
- 超出则拆分模块

---

## 设计规范

### 间距（8px 系统）
所有间距使用 8 的倍数：`8 / 16 / 24 / 32 / 48 / 64px`

### 字体层级
```
主标题：  32-48px
副标题：  20-24px
正文：    16px
辅助文字：12-14px
```

### 配色
```
主色（品牌绿）：#1a3a2a
强调色（金色）：#c9a84c
背景色（米白）：#f5f0e8
```

### 响应式断点
```
手机：< 768px
平板：768px - 1024px
桌面：> 1024px
```

### 按钮规范
- 高度：36-48px
- 左右内边距：至少是高度的 1.5 倍
- 手机端点击区域最小 44×44px

### 对齐原则
- 内容左对齐为主，标题可居中
- 避免过度居中布局

---

## 技术栈

### 前端
- 纯静态 HTML / CSS / JS，无框架
- 部署：GitHub Pages（根目录 `index.html`）

### 后端
- Python + FastAPI
- LLM：Groq（`llama-3.1-8b-instant`）
- Embedding：Google Gemini（`text-embedding-004`，512维）
- 认证：JWT（PyJWT，12小时有效期）
- 部署：Render（`render.yaml` 在仓库根目录，`rootDir: backend`）

### 数据库
- Supabase（PostgreSQL + pgvector）
- 向量维度：512
- 核心表：`documents`（content, embedding, metadata）
- 核心函数：`match_documents`（余弦相似度检索）

### RAG 流程
```
上传文档 → chunker（400字/块）→ Gemini Embedding → Supabase pgvector
用户提问 → Gemini Embedding → 向量检索 Top 5 → Groq 流式生成回答
```

## 项目结构

```
demo_Mai_Munich/
├── index.html          # 用户聊天界面
├── admin.html          # 管理员后台（文档上传/管理）
├── css/
│   ├── style.css       # 公共样式
│   └── admin.css       # 后台专属样式
├── js/
│   ├── app.js          # 聊天逻辑 + SSE
│   └── admin.js        # 后台逻辑 + JWT
├── backend/
│   ├── main.py         # FastAPI 路由
│   ├── auth.py         # JWT 登录认证
│   ├── rag/
│   │   ├── chunker.py  # 文档切块
│   │   ├── embedder.py # Gemini 向量化
│   │   └── retriever.py# Supabase 向量检索
│   ├── db/
│   │   └── client.py   # Supabase 客户端
│   ├── requirements.txt
│   ├── .env.example
│   └── supabase_init.sql
├── render.yaml         # Render 部署配置
├── .gitignore
└── CLAUDE.md
```
