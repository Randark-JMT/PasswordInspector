import pandas as pd
from contextlib import contextmanager
import re
from openpyxl.utils.exceptions import IllegalCharacterError

FAILED_LINE = []
DOMAINS = []
KEYWORD = "*2026"
KEYWORD_WHOLE_WORD = False

KEYWORD_PATTERN = (
    re.compile(rf"(?<![a-zA-Z0-9]){re.escape(KEYWORD)}(?![a-zA-Z0-9])")
    if KEYWORD and KEYWORD_WHOLE_WORD
    else None
)


def is_keyword_matched(line: str) -> bool:
    """判断当前行是否命中关键词规则。"""
    if not KEYWORD:
        return True
    if KEYWORD_WHOLE_WORD and KEYWORD_PATTERN:
        return bool(KEYWORD_PATTERN.search(line))
    return KEYWORD in line

def has_illegal_characters(text):
    """检查字符串是否包含Excel非法字符"""
    if not isinstance(text, str):
        return False
    
    # Excel不允许的字符范围
    illegal_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
    return bool(illegal_chars.search(text))


def line_paeser(line: str):
    # check if charector is error
    if has_illegal_characters(line):
        return
    # check if keyword
    if not is_keyword_matched(line):
        return

    # check if file header
    if line.startswith("TOTAL_"):
        return

    # check if cookies
    if ";" in line:
        return

    # pre-clean
    line = line.strip()

    # middle clean
    # example.com|username|password
    if line.count("|") == 2:
        line = line.replace("|", ":")
    # example.com : username : password
    if line.count(" : ") == 2:
        line = line.replace(" : ", ":")

    # extract record
    # username:password
    if line.count(":") == 1:
        parts = line.split(":")
        record = {
            "URL": "",
            "Username": parts[0],
            "Password": parts[1],
        }
    # example.com:username:password
    elif not line.startswith("http") and line.count(":") == 2 and " " not in line:
        parts = line.split(":")
        parts = [i.strip() for i in parts]
        record = {
            "URL": parts[0],
            "Username": parts[1],
            "Password": parts[2],
        }
    # example.com username:password
    elif line.count(":") == 1 and line.count(" ") == 1:
        # example.com username:password
        if line.index(":") > line.index(" "):
            line = line.replace(" ", ":")
            parts = [i[::-1].strip() for i in line[::-1].split(":", 2)]
            record = {
                "URL": parts[2],
                "Username": parts[1],
                "Password": parts[0],
            }
        # username:password example.com
        else:
            line = line.replace(" ", ":")
            parts = [i[::-1].strip() for i in line[::-1].split(":", 2)]
            record = {
                "URL": parts[0],
                "Username": parts[2],
                "Password": parts[1],
            }
    # http(s)://example.com username:password
    # username:password http(s)://example.com
    elif "http" in line and line.count(":") == 2 and line.count(" ") == 1:
        part = line.split(" ")
        record = {
            "URL": [i for i in part if "http" in i][0],
            "Username": [i for i in part if "http" not in i][0].split(":")[0],
            "Password": [i for i in part if "http" not in i][0].split(":")[1],
        }
    # example.com:username:password
    elif line.count(":") >= 3 and " " not in line:
        parts = [i[::-1].strip() for i in line[::-1].split(":", 2)]
        record = {
            "URL": parts[2],
            "Username": parts[1],
            "Password": parts[0],
        }
    else:
        FAILED_LINE.append(line)
        return
    # collect domain
    if record["URL"]:
        url = record["URL"]
        url = url.replace("http://", "").replace("https://", "")
        domain = url.split("/")[0]
        if "." in domain and domain not in DOMAINS:
            DOMAINS.append(domain)
    return record


@contextmanager
def excel_writer_safe(filename):
    """安全的Excel写入器上下文管理器"""
    writer = pd.ExcelWriter(filename, engine="openpyxl")
    try:
        yield writer
    finally:
        writer.close()


def process_huge_file_optimized(input_file, output_file, buffer_lines=100000):
    """
    针对超大文件的优化版本，使用更小的缓冲区
    """
    with excel_writer_safe(output_file) as writer:
        current_buffer = []
        row_offset = 0
        first_write = True

        with open(input_file, "r", buffering=32768, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # 解析行数据
                record = line_paeser(line)
                if record:
                    current_buffer.append(record)

                # 缓冲区满时写入
                if len(current_buffer) >= buffer_lines:
                    df_buffer = pd.DataFrame(current_buffer)
                    df_buffer.to_excel(
                        writer,
                        sheet_name="Credentials",
                        index=False,
                        header=first_write,
                        startrow=row_offset if not first_write else 0,
                    )

                    row_offset += len(current_buffer)
                    current_buffer = []
                    first_write = False

                    if line_num % 10000 == 0:
                        print(f"Progress: {line_num} lines processed")

        # 写入剩余数据
        if current_buffer:
            df_buffer = pd.DataFrame(current_buffer)
            df_buffer = df_buffer.sort_values('URL')
            df_buffer.to_excel(
                writer,
                sheet_name="Credentials",
                index=False,
                header=first_write,
                startrow=row_offset if not first_write else 0,
            )

        # 收集 domain 數據
        DOMAINS.sort()
        if DOMAINS:
            df_buffer = pd.DataFrame(DOMAINS, columns=["Domain"])
            df_buffer.to_excel(
                writer,
                sheet_name="Domains",
                index=False,
                header=first_write,
                startrow=row_offset if not first_write else 0,
            )

    print("Processing completed!")


# 使用示例
process_huge_file_optimized(
    "Z:\\sharing\\password\\.tw.txt",
    f"Z:\\sharing\\password\\{KEYWORD}.xlsx",
    buffer_lines=2000,  # 根据可用内存调整
)
print(f"\nFailed to parse line bellow:\n\n{'\n'.join(FAILED_LINE)}\n")
