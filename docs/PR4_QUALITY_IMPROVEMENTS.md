# PR #4 优质改动移植指南

> **来源**: [PR #4](https://github.com/77AutumN/Intel_Briefing/pull/4) by `gudo7208` (Claude Code via Happy)
> **审查日期**: 2026-02-13
> **目标**: 将公开仓库 PR 中的优质改动移植到私有仓库 `intel-briefing-engine`
> **状态**: 待实施

## 快速概览

| 编号 | 改动 | 优先级 | 影响文件 | 复杂度 |
|------|------|--------|----------|--------|
| 1 | SSL 证书验证修复 | 🔴 P0 | `hn_blogs.py` | 低 |
| 2 | `_dedup_items()` 去重 | 🟠 P1 | `intel_collector.py` | 低 |
| 3 | `_validate_url()` 输入验证 | 🟠 P1 | `fetch_news.py`, `verifier.py` | 低 |
| 4 | `bare except` → 具体异常 | 🟠 P1 | 全局 (15+ 处) | 中 |
| 5 | `print()` → `logging` | 🟡 P2 | 全局 | 中高 |
| 6 | `ThreadPoolExecutor` 并行化 | 🟡 P2 | `intel_collector.py` | 高 |
| 7 | `requirements.txt` 版本约束 | 🟡 P2 | `requirements.txt` | 低 |
| 8 | 单元测试框架 | 🟢 P3 | `tests/test_core.py` | 中 |
| 9 | Type Hints | 🟢 P3 | 全局 | 低 |
| 10 | 集中配置 `config.py` | 🟢 P3 | 新文件 + 全局引用 | 高 |

---

## 🔴 1. SSL 证书验证修复

### 文件: `src/sensors/hn_blogs.py`

### 问题

当前代码**完全禁用了 SSL 证书验证**，这是一个安全漏洞：

```python
# ❌ 当前代码（私有仓库 origin/main 已确认存在）
def _create_ssl_context():
    """Create SSL context that ignores certificate errors (for some blogs)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
```

`CERT_NONE` 意味着：
- 不验证服务器证书的真实性
- 容易遭受中间人攻击（MITM）
- 攻击者可以伪装成任何博客站点

### 修复方案

```python
# ✅ PR #4 的修复
def _create_ssl_context():
    """Create SSL context with proper certificate verification."""
    try:
        ctx = ssl.create_default_context()
        return ctx
    except ssl.SSLError:
        # Fallback: still verify but with reduced security rather than no security
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx
```

### 设计说明

- 默认使用 `ssl.create_default_context()` —— 这会启用完整的证书链验证
- 如果默认上下文创建失败（极罕见），回退到手动配置但**仍保持验证**
- 某些博客可能因证书过期而抓取失败，但安全性远比覆盖率重要
- 如果确实有需要跳过验证的特定站点，应该用白名单方式处理，而不是全局禁用

### 实施步骤

1. 打开 `src/sensors/hn_blogs.py`
2. 找到 `_create_ssl_context()` 函数
3. 用上述修复方案替换
4. 测试：运行情报采集看 HN Blogs 是否正常抓取

---

## 🟠 2. `_dedup_items()` 标题去重

### 文件: `src/intel_collector.py`

### 问题

多源采集时，相同新闻可能同时出现在 HN、GitHub、36Kr 等来源，导致报告中出现重复条目。

### 完整实现

```python
def _dedup_items(items: list, key: str = "title") -> list:
    """基于标题去除重复条目。
    
    Args:
        items: 情报条目列表，每个条目是 dict
        key: 用于去重的字段名，默认 "title"
    
    Returns:
        去重后的列表，保持原始顺序
    
    规则:
        - 标题 case-insensitive 比较 (strip + lower)
        - 空标题的条目保留（不参与去重）
        - 保留第一次出现的条目
    """
    seen = set()
    unique = []
    for item in items:
        title = item.get(key, "").strip().lower()
        if title and title not in seen:
            seen.add(title)
            unique.append(item)
        elif not title:
            unique.append(item)  # 空标题不去重，直接保留
    return unique
```

### 使用方式

在 `fetch_all_sources()` 返回前对每个类别去重：

```python
intel = {
    "tech_trends": _dedup_items(tech_trends_raw),
    "capital_flow": _dedup_items(capital_flow_raw),
    "community": _dedup_items(community_raw),
    # ... 其他类别
}
```

### 测试用例

```python
def test_dedup_removes_duplicates():
    items = [
        {"title": "Hello World", "url": "a"},
        {"title": "hello world", "url": "b"},  # 重复（case-insensitive）
        {"title": "Different", "url": "c"},
    ]
    result = _dedup_items(items)
    assert len(result) == 2  # "Hello World" + "Different"

def test_dedup_keeps_empty_titles():
    items = [
        {"title": "", "url": "a"},
        {"title": "", "url": "b"},
    ]
    result = _dedup_items(items)
    assert len(result) == 2  # 空标题全部保留

def test_dedup_empty_list():
    assert _dedup_items([]) == []
```

### 可选增强

如果需要更智能的去重（如标题略有不同但指同一新闻），可考虑：
- 基于 URL domain + path 的去重
- 基于 n-gram 相似度的模糊匹配（如 `difflib.SequenceMatcher`，阈值 0.85）

---

## 🟠 3. `_validate_url()` 输入验证

### 文件: `src/external/fetch_news.py`, `src/utils/verifier.py`

### 完整实现

```python
def _validate_url(url: str) -> bool:
    """Validate that a URL is well-formed.
    
    只检查基本格式，不做 DNS 解析或连接测试。
    """
    return bool(url and url.startswith(('http://', 'https://')))
```

### 使用位置

**`fetch_news.py` — `fetch_url_content()` 入口：**

```python
def fetch_url_content(url):
    # 在最开头加入验证
    if not _validate_url(url):
        return ""
    # ... 原有逻辑
```

**`verifier.py` — `verify_link()` 入口：**

```python
def verify_link(url: str, timeout: float = 5.0) -> bool:
    # 在最开头加入验证
    if not url or not url.startswith(("http://", "https://")):
        return False
    # ... 原有逻辑
```

### 测试用例

```python
def test_validate_url():
    assert _validate_url("https://example.com") is True
    assert _validate_url("http://example.com") is True
    assert _validate_url("ftp://example.com") is False
    assert _validate_url("") is False
    assert _validate_url(None) is False
```

---

## 🟠 4. `bare except` → 具体异常类型

### 影响: 全局 15+ 处

### 原则

| 原代码 | 改为 | 适用场景 |
|--------|------|----------|
| `except:` | `except (SpecificError, ...) as e:` | 所有场景 |
| `except Exception:` | `except (SpecificError, ...) as e:` | 已知异常类型时 |
| `except Exception as e:` | 保留（如果异常类型确实不可预测） | 顶层兜底 |

### 完整改动列表

#### `src/external/fetch_news.py`

```diff
# fetch_hackernews() — 网络请求
-        except: break
+        except requests.RequestException as e:
+            logger.warning(f"HN page {page} fetch failed: {e}")
+            break

# fetch_hackernews() — 行解析
-            except: continue
+            except (AttributeError, KeyError, TypeError) as e:
+                continue

# fetch_weibo()
-    except Exception:
+    except (requests.RequestException, ValueError, KeyError) as e:

# fetch_github() — 网络请求
-    except: return []
+    except requests.RequestException as e:
+        return []

# fetch_github() — 行解析
-        except: continue
+        except (AttributeError, KeyError, TypeError) as e:
+            continue

# fetch_36kr()
-    except: return []
+    except (requests.RequestException, AttributeError, KeyError, TypeError) as e:

# fetch_v2ex()
-    except: return []
+    except (requests.RequestException, ValueError, KeyError) as e:

# fetch_tencent()
-    except: return []
+    except (requests.RequestException, ValueError, KeyError, IndexError) as e:

# fetch_wallstreetcn()
-    except: return []
+    except (requests.RequestException, ValueError, KeyError) as e:

# fetch_producthunt()
-    except: return []
+    except (requests.RequestException, AttributeError, ValueError) as e:

# main() — 源循环
-        except: pass
+        except Exception as e:
+            logger.warning(f"Source {func.__name__} failed: {e}")

# fetch_url_content()
-    except Exception:
+    except (requests.RequestException, ValueError, AttributeError) as e:

# enrich_items_with_content()
-            except Exception:
+            except Exception as e:  # ThreadPool 的 future.result() 需要宽泛捕获
```

#### `src/sensors/hn_blogs.py`

```diff
# _fetch_url()
-    except Exception as e:
-        print(f"    [WARN] Failed to fetch {url[:50]}...: {e}")
+    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as e:

# parse_rss_feed()
-    except Exception as e:
-        print(f"    [WARN] Error parsing feed from {source_title}: {e}")
+    except (AttributeError, KeyError, TypeError) as e:

# fetch_hn_blogs() — 日期解析
-        except:
+        except (ValueError, TypeError, AttributeError):
```

#### `src/utils/gemini_translator.py`

```diff
# translate_to_chinese() — API 调用
-        except Exception as e:
+        except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError) as e:

# summarize_blog_article() — API 调用
-    except Exception as e:
+    except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError) as e:
```

#### `src/utils/jina_reader.py`

```diff
# fetch_full_content()
-    except Exception as e:
-        print(f"    [WARN] Jina error: {e}")
+    except (httpx.HTTPError, ValueError) as e:
```

#### `src/utils/verifier.py`

```diff
# verify_link()
-    except Exception as e:
-        print(f"  ⚠️ Link Verification Error ({url}): {e}")
+    except httpx.TimeoutException:
+        return False
+    except (httpx.HTTPError, ValueError) as e:
+        return False
```

---

## 🟡 5. `print()` → `logging` 标准化

### 模式

每个文件顶部添加：

```python
import logging
logger = logging.getLogger(__name__)
```

替换规则：

| 原始 | 替换为 |
|------|--------|
| `print(f"[*] ...")` | `logger.info(...)` |
| `print(f"[WARN] ...")` | `logger.warning(...)` |
| `print(f"[ERROR] ...")` | `logger.error(...)` |
| `print(f"    ✅ ...")` | `logger.info(...)` |
| `print(f"    ⚠️ ...")` | `logger.warning(...)` |
| `print(f"    ❌ ...")` | `logger.error(...)` |
| 调试/进度输出 | `logger.debug(...)` |

### 入口点配置

需要在 `run_mission.py` 或 `cli.py` 的入口添加 logging 初始化：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
```

### 注意事项

- CI/CD workflow 中如果依赖 stdout 输出来判断状态，切换到 logging 后需要验证
- `logging.basicConfig()` 只在第一次调用时生效（使用 `force=True` 可以强制重配置）
- 如果需要同时写日志文件，添加 `FileHandler`

### 影响文件

- `src/sensors/hn_blogs.py` — 约 12 处
- `src/external/fetch_news.py` — 约 10 处
- `src/intel_collector.py` — 约 15 处
- `src/utils/gemini_translator.py` — 约 6 处
- `src/utils/jina_reader.py` — 约 7 处
- `src/utils/verifier.py` — 约 1 处

---

## 🟡 6. `ThreadPoolExecutor` 并行化

### 文件: `src/intel_collector.py`

### 核心思路

将 `fetch_all_sources()` 中的串行采集改为并行，分两层：

**第一层**：外部源（HN, GitHub, 36Kr, WallStreetCN, V2EX）并行：

```python
def _fetch_external_sources(limit: int) -> dict:
    results = {"tech_trends": [], "capital_flow": [], "community": []}
    
    source_tasks = {
        "hn": (fetch_hackernews, "tech_trends", "Hacker News"),
        "github": (fetch_github, "tech_trends", "GitHub"),
        "36kr": (fetch_36kr, "capital_flow", "36Kr"),
        "wallstreetcn": (fetch_wallstreetcn, "capital_flow", "WallStreetCN"),
        "v2ex": (fetch_v2ex, "community", "V2EX"),
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {}
        for key, (func, category, name) in source_tasks.items():
            future = executor.submit(func, limit=limit)
            future_map[future] = (category, name)

        for future in concurrent.futures.as_completed(future_map):
            category, name = future_map[future]
            try:
                items = future.result(timeout=120)
                results[category].extend([{**item, "category": name} for item in items])
            except Exception as e:
                logger.warning(f"{name} failed: {e}")

    return results
```

**第二层**：所有源组并行（外部源、Product Hunt、ArXiv、Grok、XHS、HN Blogs）：

```python
def fetch_all_sources(limit_per_source: int = 10) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_external = executor.submit(_fetch_external_sources, limit_per_source)
        future_ph = executor.submit(_fetch_product_hunt, limit_per_source)
        future_arxiv = executor.submit(_fetch_arxiv, limit_per_source)
        future_social = executor.submit(_fetch_grok_social)
        future_xhs = executor.submit(_fetch_xhs)
        future_blogs = executor.submit(_fetch_hn_blogs, 5)

        def _safe_result(future, name, default=None):
            try:
                return future.result(timeout=120)
            except (concurrent.futures.TimeoutError, Exception) as e:
                logger.warning(f"{name} timed out or failed: {e}")
                return default if default is not None else []

        external = _safe_result(future_external, "External Sources", 
                                {"tech_trends": [], "capital_flow": [], "community": []})
        ph_data = _safe_result(future_ph, "Product Hunt")
        arxiv_data = _safe_result(future_arxiv, "ArXiv")
        # ... 其他

    intel = {
        "tech_trends": _dedup_items(external.get("tech_trends", [])),
        "capital_flow": _dedup_items(external.get("capital_flow", [])),
        "product_gems": ph_data,
        # ...
    }
    return intel
```

### 注意事项

- **timeout 120s**：每个 future.result() 都有超时保护，防止某个源卡住阻塞全部
- **`_safe_result()` 包装**：统一处理超时和异常，失败时返回空列表
- **max_workers=8**：不要太大，避免触发目标站点的 rate limit
- **Grok API 有 rate limit**：如果 Grok 同时做 Product Hunt 情感分析 + 社交情报，注意并发控制
- **需要导入**：`import concurrent.futures`

### 预期性能提升

串行模式下每源 3-5s，8个源 ≈ 30-40s → 并行后 ≈ 5-8s（取决于最慢的源）

---

## 🟡 7. `requirements.txt` 版本约束

### 改动

```diff
-httpx>=0.27
+httpx[socks]>=0.27,<1.0
-python-dotenv>=1.0
+python-dotenv>=1.0,<2.0
-feedparser>=6.0
+feedparser>=6.0,<7.0
-google-genai>=1.0
+google-genai>=1.0,<2.0
-requests>=2.31
+requests>=2.31,<3.0
-beautifulsoup4>=4.12
+beautifulsoup4>=4.12,<5.0
-lxml>=5.0
+lxml>=5.0,<6.0
```

### 说明

- **版本上限** (`<X.0`)：防止 major version 升级导致 breaking changes
- **`httpx[socks]`**：增加 SOCKS 代理支持（对代理环境有用）
- 这些库目前都没有临近 major version 升级的迹象，所以上限约束主要是防御性措施

---

## 🟢 8. 单元测试框架

### 文件: `tests/test_core.py`（新建）

PR 提供的测试覆盖以下领域（全部不依赖外部 API）：

| 测试类 | 测试内容 | 数量 |
|--------|----------|------|
| `TestDedup` | `_dedup_items()` 去重逻辑 | 3 |
| `TestReportGenerator` | 空报告 + 有数据报告生成 | 2 |
| `TestFetchNewsHelpers` | `filter_items()` + `_validate_url()` | 3 |
| `TestVerifier` | URL 格式验证 | 1 |
| `TestGrokReportValidation` | Grok 报告链接验证 | 2 |
| `TestConfig` | 配置导入 + logging 初始化 | 2 |

### 运行方式

```bash
cd D:\Intel_Briefing
pytest tests/test_core.py -v
```

### 注意

- 测试依赖 `pytest`，需要 `pip install pytest`
- `TestConfig` 类依赖 `src/config.py` 的存在，如果不实施改动 #10 则需要跳过或删除这两个测试
- 其他测试类可以独立使用

---

## 🟢 9. Type Hints

### 模式

给所有公开函数添加类型注解：

```python
# Before
def fetch_hackernews(limit=5, keyword=None):

# After
from typing import List, Dict, Optional
def fetch_hackernews(limit: int = 5, keyword: Optional[str] = None) -> List[Dict]:
```

### 影响文件

- `src/external/fetch_news.py` — 所有 `fetch_*` 函数
- `src/intel_collector.py` — `fetch_all_sources()` 和内部函数
- `src/utils/jina_reader.py` — `fetch_full_content()`

### 注意

- 不改变运行时行为，纯代码文档价值
- 如果使用 mypy 或 pyright，可以启用类型检查

---

## 🟢 10. 集中配置 `config.py`

### 文件: `src/config.py`（新建）

### 完整内容

```python
"""
Intel Briefing - 统一配置模块
所有硬编码常量集中管理
"""
import os
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

# --- Logging ---
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(level: str = "INFO", log_file: str = None):
    """配置全局日志。"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=log_level, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT,
        handlers=handlers, force=True,
    )

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PRODUCTHUNT_TOKEN = os.getenv("PRODUCTHUNT_TOKEN")

# --- API Endpoints ---
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = "gemini-2.5-flash-lite"
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1/chat/completions")
XAI_MODEL = os.getenv("XAI_MODEL", "grok-beta")
GITHUB_API_URL = "https://api.github.com/graphql"
JINA_READER_URL = "https://r.jina.ai/"

# --- Timeouts (seconds) ---
DEFAULT_TIMEOUT = 15
GEMINI_TIMEOUT = 60
JINA_TIMEOUT = 30
GROK_TIMEOUT = 60

# --- Content Limits ---
CONTENT_TRUNCATE_LIMIT = 3000
JINA_MAX_CHARS = 15000
PH_HYDRATION_TRUNCATE = 5000
GEMINI_MAX_OUTPUT_TOKENS = 1024
GEMINI_SUMMARY_MAX_TOKENS = 256
GEMINI_DETAIL_MAX_TOKENS = 1024

# --- Rate Limiting ---
GEMINI_RATE_LIMIT_DELAY = 1.5
GEMINI_MAX_RETRIES = 3

# --- Fetch Limits ---
MAX_BLOGS_TO_FETCH = 20
MAX_ARTICLES_PER_BLOG = 2
RSS_FETCH_TIMEOUT = 10
```

### 注意事项

- `GEMINI_MODEL` 硬编码为 `gemini-2.5-flash-lite`，私有仓库可能用更灵活的方式管理模型选择
- 如果私有仓库已有自己的配置管理（如 env-based 或 yaml），不建议直接引入此文件
- 各模块需要改为 `from config import GEMINI_API_KEY` 而非 `os.getenv("GEMINI_API_KEY")`

---

## 实施建议

### 推荐顺序

```
Phase 1（立即）: #1 SSL 修复
Phase 2（本周）: #2 去重 + #3 URL 验证
Phase 3（下周）: #4 具体异常类型（逐文件改）
Phase 4（择机）: #5 logging + #6 并行化
Phase 5（可选）: #7-#10
```

### 每个改动都可以独立实施

除了 #10 (`config.py`) 会影响 #5 (logging) 的配置方式外，其余改动互相独立，可以按任意顺序单独实施和测试。

### 测试验证

每次改动后建议运行完整的情报采集流程验证：

```bash
python run_mission.py
```

确认报告正常生成、各数据源正常采集。
