# Notebook MCP Server

Jupyter 노트북(.ipynb) 파일을 편집할 수 있는 MCP(Model Context Protocol) 서버입니다.

## 설치

```bash
cd d:\PythonPractice\notebook-mcp-server
pip install -e .
```

또는 uv 사용 시:

```bash
cd d:\PythonPractice\notebook-mcp-server
uv pip install -e .
```

## 사용법

### 직접 실행

```bash
python -m notebook_mcp.server
```

### Antigravity/VS Code에 등록

MCP 설정 파일에 다음을 추가하세요:

```json
{
  "mcpServers": {
    "notebook-editor": {
      "command": "python",
      "args": ["-m", "notebook_mcp.server"],
      "env": {
        "PYTHONPATH": "d:\\PythonPractice\\notebook-mcp-server\\src"
      }
    }
  }
}
```

## 제공 도구

| 도구명 | 설명 |
|--------|------|
| `read_notebook` | 노트북 전체 구조 읽기 |
| `read_cell` | 특정 셀 내용 읽기 |
| `add_cell` | 새 셀 추가 |
| `update_cell` | 셀 내용 수정 |
| `delete_cell` | 셀 삭제 |
| `move_cell` | 셀 위치 이동 |
| `update_notebook_metadata` | 노트북 메타데이터 수정 |
| `update_cell_metadata` | 셀 메타데이터 수정 |

## 라이선스

MIT
