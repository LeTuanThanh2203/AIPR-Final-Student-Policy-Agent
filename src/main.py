"""Giao diện dòng lệnh tương tác Trợ lý Điểm Rèn luyện T4 (make demo).

Phụ trách chính: Member C (Phước Anh).
Tích hợp toàn diện:
- RobustLLMClient (Groq LLM với Exponential Backoff & Timeout).
- MCPClientManager (Kết nối Stdio tới MCP Server và Dynamic Tool Discovery).
- ReActOrchestrator (Vòng lặp ReAct Think -> Act -> Observe).
- SessionLogger (Ghi trace JSONL và tính toán chi phí token).
- Giao diện dòng lệnh hiển thị trực quan, chuyên nghiệp bằng thư viện Rich.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Cấu hình chuẩn UTF-8 cho stdout và stderr trên môi trường Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo thư mục gốc dự án nằm ở đầu PYTHONPATH và loại bỏ thư mục src để không làm lu mờ gói thư viện mcp
PROJECT_ROOT = Path(__file__).resolve().parent.parent
src_dir = str(PROJECT_ROOT / "src")
while src_dir in sys.path:
    sys.path.remove(src_dir)

proj_root_str = str(PROJECT_ROOT)
if proj_root_str in sys.path:
    sys.path.remove(proj_root_str)
sys.path.insert(0, proj_root_str)

from src.llm_client import RobustLLMClient
from src.mcp.client import MCPClientManager
from src.orchestrator import ReActOrchestrator
from src.utils.logger import SessionLogger, estimate_cost


console = Console()


def render_banner() -> None:
    """Hiển thị khung giới thiệu hệ thống trực quan và sinh động bằng Rich Panel."""
    banner_text = Text()
    banner_text.append("TRỢ LÝ ĐIỂM RÈN LUYỆN & QUẢN LÝ KHIẾU NẠI SINH VIÊN\n", style="bold cyan")
    banner_text.append("Đề tài T4 - AIPR Final Project | ReAct Agent & Model Context Protocol (MCP)\n\n", style="italic white")
    banner_text.append("• 🔍 Tra cứu quy chế: ", style="bold green")
    banner_text.append("Truy xuất quy định và trích dẫn chuẩn xác Điều, Khoản (RAG)\n", style="white")
    banner_text.append("• 🧮 Tính điểm & Áp trần: ", style="bold yellow")
    banner_text.append("Tự động tính tổng điểm hoạt động và áp mức trần tối đa theo quy chế\n", style="white")
    banner_text.append("• 📝 Nộp khiếu nại: ", style="bold magenta")
    banner_text.append("Ghi nhận đơn và tự động đối soát xác minh qua CSDL (Quy tắc R-07)\n", style="white")
    banner_text.append("• 🛡️ Calibration: ", style="bold blue")
    banner_text.append("Cơ chế từ chối an toàn và lịch sự trước các câu hỏi bẫy ngoài quy chế\n\n", style="white")
    banner_text.append("Lệnh tiện ích: ", style="bold")
    banner_text.append("'help'", style="bold yellow")
    banner_text.append(" (xem câu hỏi mẫu)  |  ", style="dim")
    banner_text.append("'tools'", style="bold cyan")
    banner_text.append(" (danh sách MCP tools)  |  ", style="dim")
    banner_text.append("'exit'", style="bold red")
    banner_text.append(" / ", style="dim")
    banner_text.append("'q'", style="bold red")
    banner_text.append(" (kết thúc)", style="dim")

    console.print(Panel(banner_text, title="🎓 [bold green]AIPR - ĐỀ TÀI T4[/bold green]", border_style="cyan", padding=(1, 2)))


def render_help() -> None:
    """Hiển thị bảng câu hỏi mẫu phân theo từng tầng nghiệp vụ."""
    table = Table(title="💡 GỢI Ý CÂU HỎI MẪU THEO TỪNG TẦNG NGHIỆP VỤ", border_style="cyan", header_style="bold magenta")
    table.add_column("Tầng nghiệp vụ", style="bold yellow", width=18)
    table.add_column("Mục đích kiểm thử", style="cyan", width=24)
    table.add_column("Câu hỏi mẫu cho sinh viên", style="white")

    table.add_row(
        "Tầng a (Lookup)",
        "Tra cứu quy chế RAG",
        "Sinh viên tham gia hoạt động nghiên cứu khoa học được cộng bao nhiêu điểm theo quy chế?",
    )
    table.add_row(
        "Tầng b (Transform)",
        "Tính toán & Áp trần",
        "Kỳ này tôi tham gia 3 buổi hội thảo (5đ/buổi) và hiến máu nhân đạo (10đ), tổng điểm mục này của tôi là bao nhiêu?",
    )
    table.add_row(
        "Tầng c (Action)",
        "Nộp đơn & Verify R-07",
        "Tôi muốn nộp khiếu nại vì bị thiếu 10 điểm hoạt động Tiếp sức mùa thi. Mã SV: 22120001, Họ tên: Nguyễn Văn A, Học kỳ: 1, Năm học: 2024-2025",
    )
    table.add_row(
        "Calibration",
        "Từ chối câu bẫy",
        "Quy chế có cho phép đổi chứng chỉ bằng lái xe máy sang điểm rèn luyện không?",
    )
    console.print(table)


async def render_tools(mcp_manager: MCPClientManager) -> None:
    """Hiển thị bảng danh sách các công cụ MCP khả dụng được khám phá động."""
    try:
        tools = await mcp_manager.list_tools()
        table = Table(title=f"🛠️ DANH SÁCH {len(tools)} CÔNG CỤ MCP KHẢ DỤNG", border_style="green", header_style="bold blue")
        table.add_column("STT", style="dim", width=5, justify="center")
        table.add_column("Tên công cụ (Tool Name)", style="bold green", width=28)
        table.add_column("Mô tả chức năng", style="white")

        for idx, t in enumerate(tools, start=1):
            t_name = getattr(t, "name", str(t))
            t_desc = getattr(t, "description", "")
            table.add_row(str(idx), t_name, t_desc)

        console.print(table)
    except Exception as err:
        console.print(f"[bold red][Lỗi][/bold red] Không thể liệt kê công cụ: {err}")


async def run_interactive_cli() -> None:
    """Khởi chạy vòng lặp tương tác dòng lệnh với người dùng."""
    render_banner()

    # Khởi tạo các thành phần nền tảng của hệ thống
    llm_client = RobustLLMClient()
    logger = SessionLogger(log_dir="logs")
    mcp_manager = MCPClientManager()

    # Kết nối tới MCP Server qua Stdio
    try:
        await mcp_manager.connect()
        console.print("[bold green]✔[/bold green] [dim]Đã kết nối thành công tới MCP Server qua giao thức stdio.[/dim]\n")
    except Exception as err:
        console.print(f"[bold yellow]⚠ [Cảnh báo][/bold yellow] Kết nối MCP Server gặp sự cố: {err}. Chuyển sang chế độ chạy độc lập.\n")

    orchestrator = ReActOrchestrator(
        llm_client=llm_client,
        mcp_client=mcp_manager,
        logger=logger,
        max_steps=10,
    )

    query_counter = 0
    model_name = os.getenv("MODEL", "openai/gpt-oss-20b")

    try:
        while True:
            try:
                user_input = console.input("[bold green]Sinh viên[/bold green] [bold cyan]>[/bold cyan] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Nhận tín hiệu ngắt. Đang thoát chương trình...[/dim]")
                break

            if not user_input:
                continue

            # Xử lý các lệnh điều khiển phiên
            lower_input = user_input.lower()
            if lower_input in ["exit", "quit", "q"]:
                console.print(
                    Panel(
                        "[bold green]Cảm ơn bạn đã sử dụng Trợ lý Điểm Rèn luyện T4. Chúc bạn một ngày tốt lành![/bold green]",
                        border_style="green",
                    )
                )
                break
            elif lower_input == "help":
                render_help()
                continue
            elif lower_input == "tools":
                await render_tools(mcp_manager)
                continue

            query_counter += 1
            query_id = f"CLI_{query_counter:03d}"
            console.print("\n[bold cyan]⏳ [Hệ thống][/bold cyan] [dim]Đang kích hoạt ReAct Agent phân tích và xử lý truy vấn...[/dim]")

            try:
                # Gửi câu hỏi vào ReAct Agent và nhận toàn bộ thông tin chi tiết
                res = await orchestrator.arun(user_input, return_details=True)
                if not isinstance(res, dict):
                    res = {"final_answer": str(res), "steps": [], "usage": {}}

                # Hiển thị các bước suy luận trung gian của ReAct Agent bằng Rich Table
                steps = res.get("steps") or []
                if steps:
                    step_table = Table(
                        title=f"⚡ TIẾN TRÌNH SUY LUẬN REACT ({len(steps)} BƯỚC)",
                        border_style="yellow",
                        header_style="bold yellow",
                    )
                    step_table.add_column("Bước", style="bold cyan", width=8, justify="center")
                    step_table.add_column("Hành động", style="yellow", width=16)
                    step_table.add_column("Nội dung chi tiết / Công cụ thực thi", style="white")

                    for s in steps:
                        s_num = str(s.get("step_number", ""))
                        action = s.get("action", "")
                        tool = s.get("tool_name")
                        if tool:
                            step_table.add_row(
                                f"Bước {s_num}",
                                "Gọi công cụ",
                                f"[bold green]{tool}[/bold green] với tham số: [dim]{s.get('tool_args')}[/dim]",
                            )
                        elif action == "final_answer":
                            step_table.add_row(f"Bước {s_num}", "Kết luận", "Đã thu thập đủ thông tin để đưa ra câu trả lời cuối cùng.")
                        elif s.get("error"):
                            step_table.add_row(f"Bước {s_num}", "[bold red]Lỗi[/bold red]", f"[red]{s.get('error')}[/red]")

                    console.print(step_table)

                # Hiển thị câu trả lời cuối cùng trong Rich Panel đẹp mắt với Markdown
                final_answer_text = res.get("final_answer", "").strip()
                console.print(
                    Panel(
                        Markdown(final_answer_text) if final_answer_text else "[italic dim]Không có phản hồi[/italic dim]",
                        title="🤖 [bold green]TRỢ LÝ T4 TRẢ LỜI[/bold green]",
                        border_style="green",
                        padding=(1, 2),
                    )
                )

                # Hiển thị thanh thống kê tài nguyên bằng Rich Panel
                usage = res.get("usage") or {}
                p_tokens = usage.get("prompt_tokens", 0)
                c_tokens = usage.get("completion_tokens", 0)
                tot_tokens = p_tokens + c_tokens
                cost = estimate_cost(model_name, p_tokens, c_tokens)

                stats_text = (
                    f"📊 [bold]Số bước:[/bold] [cyan]{len(steps)}[/cyan]  |  "
                    f"🪙 [bold]Tokens:[/bold] [cyan]{tot_tokens:,}[/cyan] (Input: {p_tokens:,}, Output: {c_tokens:,})  |  "
                    f"💵 [bold]Chi phí API:[/bold] [bold yellow]${cost:.6f} USD[/bold yellow]  |  "
                    f"🧠 [bold]Model:[/bold] [dim]{model_name}[/dim]"
                )
                console.print(Panel(stats_text, border_style="blue", padding=(0, 1)))
                console.print()

            except Exception as exc:
                console.print(f"[bold red][Lỗi thực thi][/bold red] Có lỗi xảy ra trong quá trình xử lý: {exc}\n")

    finally:
        # Đảm bảo đóng kết nối tiến trình MCP Server khi kết thúc chương trình
        await mcp_manager.close()


def main() -> None:
    """Điểm vào chính đồng bộ cho lệnh `make demo`."""
    asyncio.run(run_interactive_cli())


if __name__ == "__main__":
    main()
