"""
Notebook MCP Server
====================
Jupyter 노트북(.ipynb) 파일을 편집하기 위한 MCP 서버입니다.

MCP(Model Context Protocol)란?
- AI와 외부 도구 간의 표준 통신 프로토콜입니다.
- 이 서버를 통해 AI가 노트북 파일을 직접 읽고 수정할 수 있습니다.

사용하는 라이브러리:
- mcp: MCP 프로토콜 구현체 (FastMCP 프레임워크 포함)
- nbformat: Jupyter 노트북 파일을 파싱하고 저장하는 공식 라이브러리
"""

from mcp.server.fastmcp import FastMCP
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell
import json
from typing import Optional, Literal
from pathlib import Path


# ============================================================
# MCP 서버 초기화
# ============================================================
# FastMCP: MCP 서버를 쉽게 만들 수 있게 해주는 고수준 프레임워크
# 데코레이터(@mcp.tool())를 사용해서 함수를 MCP 도구로 등록합니다.

mcp = FastMCP("Notebook Editor")


# ============================================================
# 헬퍼 함수들
# ============================================================

def _load_notebook(path: str) -> nbformat.NotebookNode:
    """
    노트북 파일을 읽어서 NotebookNode 객체로 반환합니다.
    
    NotebookNode란?
    - nbformat 라이브러리가 제공하는 노트북 데이터 구조입니다.
    - 딕셔너리처럼 접근할 수 있습니다 (예: nb['cells'], nb.cells)
    """
    # as_version=4: 노트북 포맷 버전 4로 읽기 (현재 표준)
    return nbformat.read(path, as_version=4)


def _save_notebook(nb: nbformat.NotebookNode, path: str) -> None:
    """
    NotebookNode 객체를 파일로 저장합니다.
    """
    nbformat.write(nb, path)


def _validate_cell_index(nb: nbformat.NotebookNode, index: int) -> None:
    """
    셀 인덱스가 유효한지 검증합니다.
    유효하지 않으면 예외를 발생시킵니다.
    """
    if index < 0 or index >= len(nb.cells):
        raise ValueError(
            f"셀 인덱스 {index}가 범위를 벗어났습니다. "
            f"유효 범위: 0 ~ {len(nb.cells) - 1}"
        )


def _format_cell_summary(cell, index: int) -> str:
    """
    셀 정보를 한 줄 요약으로 포맷합니다.
    """
    cell_type = cell.cell_type  # 'code' 또는 'markdown'
    source = cell.source
    
    # 소스 코드 미리보기 (첫 50자)
    preview = source[:50].replace('\n', ' ')
    if len(source) > 50:
        preview += "..."
    
    return f"[{index}] {cell_type}: {preview}"


# ============================================================
# MCP 도구들 - 읽기 도구
# ============================================================

@mcp.tool()
def read_notebook(path: str) -> str:
    """
    노트북 파일의 전체 구조를 읽어 반환합니다.
    
    각 셀의 인덱스, 타입(code/markdown), 내용 미리보기를 보여줍니다.
    
    Args:
        path: 노트북 파일의 절대 경로 (예: "d:/PythonPractice/test.ipynb")
    
    Returns:
        노트북 구조 요약 문자열
    """
    nb = _load_notebook(path)
    
    # 노트북 기본 정보
    result = []
    result.append(f"📓 노트북: {Path(path).name}")
    result.append(f"   총 셀 개수: {len(nb.cells)}")
    
    # 커널 정보 (있는 경우)
    if 'kernelspec' in nb.metadata:
        kernel = nb.metadata.kernelspec.get('display_name', 'Unknown')
        result.append(f"   커널: {kernel}")
    
    result.append("")
    result.append("📋 셀 목록:")
    result.append("-" * 60)
    
    # 각 셀 요약
    for i, cell in enumerate(nb.cells):
        result.append(_format_cell_summary(cell, i))
    
    return "\n".join(result)


@mcp.tool()
def read_cell(path: str, cell_index: int) -> str:
    """
    특정 셀의 상세 내용을 읽어 반환합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 읽을 셀의 인덱스 (0부터 시작)
    
    Returns:
        셀의 상세 정보 (타입, 소스, 메타데이터, 출력 등)
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    cell = nb.cells[cell_index]
    
    result = []
    result.append(f"📝 셀 #{cell_index}")
    result.append(f"   타입: {cell.cell_type}")
    result.append("")
    result.append("📄 소스 코드:")
    result.append("-" * 40)
    result.append(cell.source)
    result.append("-" * 40)
    
    # 메타데이터 (있는 경우)
    if cell.metadata:
        result.append("")
        result.append("🏷️ 메타데이터:")
        result.append(json.dumps(dict(cell.metadata), indent=2, ensure_ascii=False))
    
    # 코드 셀인 경우 출력 정보도 표시
    if cell.cell_type == 'code' and hasattr(cell, 'outputs') and cell.outputs:
        result.append("")
        result.append(f"📤 출력: {len(cell.outputs)}개")
        for i, output in enumerate(cell.outputs):
            output_type = output.get('output_type', 'unknown')
            result.append(f"   [{i}] {output_type}")
    
    return "\n".join(result)


# ============================================================
# MCP 도구들 - 셀 추가/수정/삭제
# ============================================================

@mcp.tool()
def add_cell(
    path: str,
    cell_type: Literal["code", "markdown"],
    source: str,
    position: Optional[int] = None
) -> str:
    """
    노트북에 새 셀을 추가합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_type: 셀 타입 ("code" 또는 "markdown")
        source: 셀에 들어갈 내용
        position: 삽입 위치 (None이면 맨 끝에 추가)
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    
    # 셀 타입에 따라 새 셀 생성
    if cell_type == "code":
        new_cell = new_code_cell(source=source)
    else:
        new_cell = new_markdown_cell(source=source)
    
    # 위치 결정
    if position is None:
        position = len(nb.cells)  # 맨 끝
    elif position < 0 or position > len(nb.cells):
        raise ValueError(
            f"삽입 위치 {position}이 유효하지 않습니다. "
            f"유효 범위: 0 ~ {len(nb.cells)}"
        )
    
    # 셀 삽입
    nb.cells.insert(position, new_cell)
    _save_notebook(nb, path)
    
    return f"✅ {cell_type} 셀을 위치 {position}에 추가했습니다. (현재 총 {len(nb.cells)}개 셀)"


@mcp.tool()
def update_cell(path: str, cell_index: int, new_source: str) -> str:
    """
    특정 셀의 내용을 수정합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 수정할 셀의 인덱스 (0부터 시작)
        new_source: 새로운 셀 내용
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    old_preview = nb.cells[cell_index].source[:30].replace('\n', ' ')
    nb.cells[cell_index].source = new_source
    
    _save_notebook(nb, path)
    
    new_preview = new_source[:30].replace('\n', ' ')
    return (
        f"✅ 셀 #{cell_index} 수정 완료\n"
        f"   이전: {old_preview}...\n"
        f"   이후: {new_preview}..."
    )


@mcp.tool()
def delete_cell(path: str, cell_index: int) -> str:
    """
    특정 셀을 삭제합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 삭제할 셀의 인덱스 (0부터 시작)
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    deleted_cell = nb.cells.pop(cell_index)
    deleted_preview = deleted_cell.source[:30].replace('\n', ' ')
    
    _save_notebook(nb, path)
    
    return (
        f"🗑️ 셀 #{cell_index} 삭제 완료\n"
        f"   삭제된 내용: {deleted_preview}...\n"
        f"   남은 셀 개수: {len(nb.cells)}"
    )


@mcp.tool()
def move_cell(path: str, from_index: int, to_index: int) -> str:
    """
    셀의 위치를 이동합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        from_index: 이동할 셀의 현재 인덱스
        to_index: 이동할 목적지 인덱스
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, from_index)
    
    if to_index < 0 or to_index >= len(nb.cells):
        raise ValueError(
            f"목적지 인덱스 {to_index}가 범위를 벗어났습니다. "
            f"유효 범위: 0 ~ {len(nb.cells) - 1}"
        )
    
    # 셀 추출 후 새 위치에 삽입
    cell = nb.cells.pop(from_index)
    nb.cells.insert(to_index, cell)
    
    _save_notebook(nb, path)
    
    cell_preview = cell.source[:30].replace('\n', ' ')
    return (
        f"🔀 셀 이동 완료\n"
        f"   {from_index} → {to_index}\n"
        f"   내용: {cell_preview}..."
    )


# ============================================================
# MCP 도구들 - 메타데이터 수정
# ============================================================

@mcp.tool()
def update_notebook_metadata(path: str, key: str, value: str) -> str:
    """
    노트북의 메타데이터를 수정합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        key: 메타데이터 키 (예: "title", "author")
        value: 설정할 값 (JSON 문자열 형식, 예: '"My Title"' 또는 '{"name": "value"}')
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    
    # value를 JSON으로 파싱 (문자열, 숫자, 객체 등 지원)
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 그냥 문자열로 사용
        parsed_value = value
    
    nb.metadata[key] = parsed_value
    _save_notebook(nb, path)
    
    return f"✅ 노트북 메타데이터 수정: {key} = {parsed_value}"


@mcp.tool()
def update_cell_metadata(
    path: str, 
    cell_index: int, 
    key: str, 
    value: str
) -> str:
    """
    특정 셀의 메타데이터를 수정합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 수정할 셀의 인덱스
        key: 메타데이터 키
        value: 설정할 값 (JSON 문자열 형식)
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    # value를 JSON으로 파싱
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    nb.cells[cell_index].metadata[key] = parsed_value
    _save_notebook(nb, path)
    
    return f"✅ 셀 #{cell_index} 메타데이터 수정: {key} = {parsed_value}"


# ============================================================
# 서버 실행
# ============================================================

def main():
    """
    MCP 서버를 실행합니다.
    
    실행 방법:
    1. 직접 실행: python -m notebook_mcp.server
    2. 모듈로 호출: python -c "from notebook_mcp.server import main; main()"
    """
    # mcp.run()은 stdio 전송 방식으로 서버를 시작합니다.
    # stdio란? 표준 입출력(stdin/stdout)을 통해 메시지를 주고받는 방식입니다.
    # IDE(Antigravity)가 이 서버를 자식 프로세스로 실행하고 통신합니다.
    mcp.run()


# 이 파일을 직접 실행했을 때만 서버 시작
if __name__ == "__main__":
    main()
