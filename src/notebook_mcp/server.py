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
import re
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
# MCP 도구들 - 검색 및 교체
# ============================================================

@mcp.tool()
def search_notebook(
    path: str,
    pattern: str,
    use_regex: bool = False,
    case_sensitive: bool = True
) -> str:
    """
    노트북 전체에서 텍스트를 검색합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        pattern: 검색할 텍스트 또는 정규식 패턴
        use_regex: True면 정규식으로 검색 (default: False)
        case_sensitive: True면 대소문자 구분 (default: True)
    
    Returns:
        검색 결과 (셀 인덱스, 타입, 매칭 내용)
    """
    nb = _load_notebook(path)
    
    # 검색 플래그 설정
    flags = 0 if case_sensitive else re.IGNORECASE
    
    # 정규식이 아니면 패턴을 이스케이프 처리
    if not use_regex:
        pattern = re.escape(pattern)
    
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"❌ 정규식 오류: {e}"
    
    results = []
    total_matches = 0
    
    for i, cell in enumerate(nb.cells):
        matches = list(regex.finditer(cell.source))
        if matches:
            total_matches += len(matches)
            results.append(f"\n📍 셀 #{i} ({cell.cell_type})")
            results.append("-" * 40)
            
            # 각 매치의 컨텍스트 표시
            for match in matches:
                start = max(0, match.start() - 20)
                end = min(len(cell.source), match.end() + 20)
                context = cell.source[start:end].replace('\n', '↵')
                
                # 매칭 부분 강조
                match_text = match.group()
                results.append(f"   ...{context}...")
                results.append(f"   └─ 매칭: '{match_text}'")
    
    if total_matches == 0:
        return f"🔍 검색 결과 없음: '{pattern}'"
    
    header = f"🔍 검색 결과: {total_matches}개 매칭 ('{pattern}')"
    return header + "\n" + "\n".join(results)


@mcp.tool()
def replace_in_notebook(
    path: str,
    pattern: str,
    replacement: str,
    use_regex: bool = False,
    case_sensitive: bool = True,
    preview_only: bool = True
) -> str:
    """
    노트북 전체에서 텍스트를 일괄 교체합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        pattern: 검색할 텍스트 또는 정규식 패턴
        replacement: 교체할 텍스트
        use_regex: True면 정규식으로 검색 (default: False)
        case_sensitive: True면 대소문자 구분 (default: True)
        preview_only: True면 미리보기만 (실제 교체 안 함), False면 실제 교체 (default: True)
    
    Returns:
        교체 결과 또는 미리보기
    """
    nb = _load_notebook(path)
    
    # 검색 플래그 설정
    flags = 0 if case_sensitive else re.IGNORECASE
    
    # 정규식이 아니면 패턴을 이스케이프 처리
    if not use_regex:
        pattern = re.escape(pattern)
    
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"❌ 정규식 오류: {e}"
    
    changes = []
    total_replacements = 0
    
    for i, cell in enumerate(nb.cells):
        matches = list(regex.finditer(cell.source))
        if matches:
            count = len(matches)
            total_replacements += count
            
            # 변경 전후 미리보기
            old_preview = cell.source[:50].replace('\n', '↵')
            new_source = regex.sub(replacement, cell.source)
            new_preview = new_source[:50].replace('\n', '↵')
            
            changes.append(f"\n📝 셀 #{i} ({cell.cell_type}) - {count}개 교체")
            changes.append(f"   전: {old_preview}...")
            changes.append(f"   후: {new_preview}...")
            
            # 실제 교체 (미리보기가 아닌 경우)
            if not preview_only:
                nb.cells[i].source = new_source
    
    if total_replacements == 0:
        return f"🔍 교체 대상 없음: '{pattern}'"
    
    if preview_only:
        header = f"👁️ 미리보기: {total_replacements}개 교체 예정 ('{pattern}' → '{replacement}')"
        footer = "\n\nℹ️ 실제 교체를 원하면 preview_only=False로 호출하세요."
        return header + "\n" + "\n".join(changes) + footer
    else:
        _save_notebook(nb, path)
        header = f"✅ 교체 완료: {total_replacements}개 ('{pattern}' → '{replacement}')"
        return header + "\n" + "\n".join(changes)
# ============================================================
# MCP 도구들 - 컨텍스트 및 분석 (Cline 영감)
# ============================================================

@mcp.tool()
def get_cell_context(
    path: str,
    cell_index: int,
    context_size: int = 2
) -> str:
    """
    특정 셀과 주변 셀들의 컨텍스트를 구조화된 형태로 반환합니다.
    
    AI가 새 코드를 생성하거나 개선할 때 더 나은 컨텍스트를 파악할 수 있도록,
    대상 셀과 주변 셀들의 정보를 함께 제공합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 대상 셀의 인덱스 (0부터 시작)
        context_size: 앞뒤로 포함할 셀 개수 (기본값: 2)
    
    Returns:
        셀 컨텍스트 정보 (JSON 형식)
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    # 컨텍스트 범위 계산
    start_idx = max(0, cell_index - context_size)
    end_idx = min(len(nb.cells), cell_index + context_size + 1)
    
    def _extract_cell_info(cell, idx: int, is_target: bool = False) -> dict:
        """셀 정보를 딕셔너리로 추출"""
        info = {
            "index": idx,
            "cell_type": cell.cell_type,
            "source": cell.source,
            "is_target": is_target
        }
        
        # 코드 셀인 경우 추가 정보
        if cell.cell_type == "code":
            info["execution_count"] = getattr(cell, "execution_count", None)
            
            # 출력 정보 추가
            if hasattr(cell, "outputs") and cell.outputs:
                outputs_summary = []
                for output in cell.outputs:
                    output_type = output.get("output_type", "unknown")
                    output_info = {"type": output_type}
                    
                    # 출력 내용 미리보기
                    if output_type == "stream":
                        text = output.get("text", "")
                        output_info["preview"] = text[:200] + ("..." if len(text) > 200 else "")
                    elif output_type in ("execute_result", "display_data"):
                        data = output.get("data", {})
                        if "text/plain" in data:
                            text = "".join(data["text/plain"]) if isinstance(data["text/plain"], list) else data["text/plain"]
                            output_info["preview"] = text[:200] + ("..." if len(text) > 200 else "")
                    elif output_type == "error":
                        output_info["ename"] = output.get("ename", "")
                        output_info["evalue"] = output.get("evalue", "")
                    
                    outputs_summary.append(output_info)
                info["outputs"] = outputs_summary
        
        return info
    
    # 컨텍스트 수집
    context = {
        "notebook": Path(path).name,
        "total_cells": len(nb.cells),
        "context_range": f"{start_idx}-{end_idx - 1}",
        "cells": []
    }
    
    for idx in range(start_idx, end_idx):
        is_target = (idx == cell_index)
        cell_info = _extract_cell_info(nb.cells[idx], idx, is_target)
        context["cells"].append(cell_info)
    
    return json.dumps(context, indent=2, ensure_ascii=False)


@mcp.tool()
def get_notebook_variables(path: str) -> str:
    """
    노트북에서 사용된 import 문과 정의된 변수/함수/클래스를 추출합니다.
    
    AI가 새 코드를 생성할 때 이미 존재하는 import와 변수를 
    파악할 수 있도록 정적 분석을 수행합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
    
    Returns:
        추출된 import 및 정의 목록
    """
    nb = _load_notebook(path)
    
    imports = []
    variables = []
    functions = []
    classes = []
    
    # 정규식 패턴들
    import_pattern = re.compile(r'^(?:from\s+[\w.]+\s+)?import\s+.+', re.MULTILINE)
    variable_pattern = re.compile(r'^(\w+)\s*=\s*(?!.*def\s|.*class\s)', re.MULTILINE)
    function_pattern = re.compile(r'^def\s+(\w+)\s*\(', re.MULTILINE)
    class_pattern = re.compile(r'^class\s+(\w+)\s*[\(:]', re.MULTILINE)
    
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        
        source = cell.source
        
        # import 문 추출
        for match in import_pattern.finditer(source):
            imports.append({
                "cell": i,
                "statement": match.group().strip()
            })
        
        # 변수 정의 추출
        for match in variable_pattern.finditer(source):
            var_name = match.group(1)
            if not var_name.startswith("_"):  # private 변수 제외
                variables.append({
                    "cell": i,
                    "name": var_name
                })
        
        # 함수 정의 추출
        for match in function_pattern.finditer(source):
            functions.append({
                "cell": i,
                "name": match.group(1)
            })
        
        # 클래스 정의 추출
        for match in class_pattern.finditer(source):
            classes.append({
                "cell": i,
                "name": match.group(1)
            })
    
    result = []
    result.append(f"📦 노트북 분석: {Path(path).name}")
    result.append("=" * 50)
    
    if imports:
        result.append(f"\n📥 Import 문 ({len(imports)}개):")
        for imp in imports:
            result.append(f"   [셀 {imp['cell']}] {imp['statement']}")
    
    if variables:
        result.append(f"\n📊 변수 ({len(variables)}개):")
        var_names = [v['name'] for v in variables]
        result.append(f"   {', '.join(var_names)}")
    
    if functions:
        result.append(f"\n🔧 함수 ({len(functions)}개):")
        for func in functions:
            result.append(f"   [셀 {func['cell']}] def {func['name']}()")
    
    if classes:
        result.append(f"\n🏛️ 클래스 ({len(classes)}개):")
        for cls in classes:
            result.append(f"   [셀 {cls['cell']}] class {cls['name']}")
    
    if not any([imports, variables, functions, classes]):
        result.append("\n(정의된 항목이 없습니다)")
    
    return "\n".join(result)


@mcp.tool()
def read_cell_output(path: str, cell_index: int) -> str:
    """
    셀의 출력 내용을 상세히 반환합니다.
    
    read_cell과 달리 출력의 실제 내용을 포함하여 반환합니다.
    스트림 출력, 실행 결과, 에러 등 모든 출력 타입을 처리합니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 읽을 셀의 인덱스 (0부터 시작)
    
    Returns:
        셀 출력의 상세 내용
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    cell = nb.cells[cell_index]
    
    if cell.cell_type != "code":
        return f"ℹ️ 셀 #{cell_index}은 {cell.cell_type} 셀입니다. 출력이 없습니다."
    
    if not hasattr(cell, "outputs") or not cell.outputs:
        return f"ℹ️ 셀 #{cell_index}에 출력이 없습니다."
    
    result = []
    result.append(f"📤 셀 #{cell_index} 출력 ({len(cell.outputs)}개)")
    result.append("=" * 50)
    
    for i, output in enumerate(cell.outputs):
        output_type = output.get("output_type", "unknown")
        result.append(f"\n[{i}] {output_type}")
        result.append("-" * 40)
        
        if output_type == "stream":
            # stdout/stderr 출력
            name = output.get("name", "stdout")
            text = output.get("text", "")
            result.append(f"({name})")
            result.append(text)
            
        elif output_type == "execute_result":
            # 실행 결과
            data = output.get("data", {})
            exec_count = output.get("execution_count", "?")
            result.append(f"(execution_count: {exec_count})")
            
            if "text/plain" in data:
                text = data["text/plain"]
                if isinstance(text, list):
                    text = "".join(text)
                result.append(text)
            
            if "text/html" in data:
                result.append("\n[HTML 출력 있음 - text/html]")
                
        elif output_type == "display_data":
            # 디스플레이 데이터 (시각화 등)
            data = output.get("data", {})
            
            if "text/plain" in data:
                text = data["text/plain"]
                if isinstance(text, list):
                    text = "".join(text)
                result.append(text)
            
            # 이미지 타입 확인
            image_types = ["image/png", "image/jpeg", "image/svg+xml"]
            for img_type in image_types:
                if img_type in data:
                    result.append(f"\n[이미지 출력 있음 - {img_type}]")
                    break
                    
        elif output_type == "error":
            # 에러 출력
            ename = output.get("ename", "Error")
            evalue = output.get("evalue", "")
            result.append(f"❌ {ename}: {evalue}")
            
            traceback = output.get("traceback", [])
            if traceback:
                result.append("\nTraceback:")
                # ANSI 코드 제거
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                for line in traceback[-5:]:  # 마지막 5줄만
                    clean_line = ansi_escape.sub('', line)
                    result.append(clean_line)
    
    return "\n".join(result)


# ============================================================
# MCP 도구들 - 셀 조작 확장
# ============================================================

@mcp.tool()
def duplicate_cell(path: str, cell_index: int) -> str:
    """
    셀을 복제하여 바로 아래에 삽입합니다.
    
    실험이나 반복 작업 시 기존 셀을 복사해서 수정할 때 유용합니다.
    셀의 소스, 타입, 메타데이터가 모두 복사됩니다. (출력은 제외)
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 복제할 셀의 인덱스 (0부터 시작)
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    original_cell = nb.cells[cell_index]
    
    # 새 셀 생성 (출력 제외)
    if original_cell.cell_type == "code":
        new_cell = new_code_cell(source=original_cell.source)
    else:
        new_cell = new_markdown_cell(source=original_cell.source)
    
    # 메타데이터 복사
    new_cell.metadata = dict(original_cell.metadata)
    
    # 바로 아래에 삽입
    insert_position = cell_index + 1
    nb.cells.insert(insert_position, new_cell)
    
    _save_notebook(nb, path)
    
    preview = original_cell.source[:40].replace('\n', ' ')
    return (
        f"📋 셀 #{cell_index} 복제 완료\n"
        f"   새 셀 위치: #{insert_position}\n"
        f"   내용: {preview}..."
    )


@mcp.tool()
def change_cell_type(
    path: str,
    cell_index: int,
    new_type: Literal["code", "markdown"]
) -> str:
    """
    셀의 타입을 변경합니다 (code ↔ markdown).
    
    코드 셀을 마크다운으로 변환하면 출력과 execution_count가 제거됩니다.
    소스 내용은 그대로 유지됩니다.
    
    Args:
        path: 노트북 파일의 절대 경로
        cell_index: 변경할 셀의 인덱스 (0부터 시작)
        new_type: 변경할 셀 타입 ("code" 또는 "markdown")
    
    Returns:
        성공 메시지
    """
    nb = _load_notebook(path)
    _validate_cell_index(nb, cell_index)
    
    old_cell = nb.cells[cell_index]
    old_type = old_cell.cell_type
    
    if old_type == new_type:
        return f"ℹ️ 셀 #{cell_index}은 이미 {new_type} 타입입니다."
    
    # 새 셀 생성 (소스 유지)
    source = old_cell.source
    
    if new_type == "code":
        new_cell = new_code_cell(source=source)
    else:
        new_cell = new_markdown_cell(source=source)
    
    # 메타데이터 복사 (가능한 것만)
    for key, value in old_cell.metadata.items():
        new_cell.metadata[key] = value
    
    # 셀 교체
    nb.cells[cell_index] = new_cell
    
    _save_notebook(nb, path)
    
    preview = source[:40].replace('\n', ' ')
    return (
        f"🔄 셀 #{cell_index} 타입 변경 완료\n"
        f"   {old_type} → {new_type}\n"
        f"   내용: {preview}..."
    )


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
