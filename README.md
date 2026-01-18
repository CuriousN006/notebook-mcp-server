# Notebook MCP Server

Jupyter 노트북(.ipynb) 파일을 편집할 수 있는 MCP(Model Context Protocol) 서버입니다.

## 설치

```bash
git clone https://github.com/CuriousN006/notebook-mcp-server.git
cd notebook-mcp-server
pip install -e .
```

또는 uv 사용 시:

```bash
cd notebook-mcp-server
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
        "PYTHONPATH": "/path/to/notebook-mcp-server/src"
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

## AI 시스템 프롬프트 (권장)

AI 어시스턴트가 이 MCP 서버를 올바르게 사용하도록 다음 내용을 시스템 프롬프트에 추가하세요:

```markdown
- .ipynb 형식 노트북 파일은 `notebook-editor` MCP 서버를 통해 직접 수정합니다.
  - 사용 가능한 도구:
    - read_notebook: 노트북 전체 구조 읽기
    - read_cell: 특정 셀 내용 읽기
    - add_cell: 새 셀 추가 (code/markdown)
    - update_cell: 셀 내용 수정
    - delete_cell: 셀 삭제
    - move_cell: 셀 위치 이동
    - update_notebook_metadata: 노트북 메타데이터 수정
    - update_cell_metadata: 셀 메타데이터 수정
  - 노트북 경로는 반드시 절대 경로로 지정하세요 (예: `/path/to/notebook.ipynb`)
  - ⚠️ **주의사항**: 노트북 수정 전에 VS Code에서 해당 파일이 **저장된 상태**인지 확인하세요.
    - 셀 실행 후 저장하지 않은 상태에서 MCP로 수정하면, VS Code가 덮어써서 수정이 유실될 수 있습니다.
    - 수정 요청 시 사용자에게 "파일을 저장(Ctrl+S)했는지" 먼저 확인해주세요.
```

## 라이선스

MIT
