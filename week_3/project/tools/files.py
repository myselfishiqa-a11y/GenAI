import os
import glob as glob_module

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))


def resolve_path(path: str) -> str:   #This is not a file tool - it is a helper function for file tools.

    full=os.path.abspath(os.path.join(WORKSPACE_ROOT,path))
    root=os.path.abspath(WORKSPACE_ROOT)

    if not ((full==root) or full.startswith(root+os.sep)):
        raise ValueError("Path escapes workspace.")
    
    return full


def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> dict:
    try:
        file_path=resolve_path(path)
        with open(file_path,"r") as handle:
            lines=handle.readlines()

    except (ValueError,FileNotFoundError) as e:
            return {"error":str(e)}
    
    total_lines=len(lines)
    selected=lines[start_line-1:start_line-1+read_lines]

    numbered=""
    for i,line in enumerate(selected,start=start_line):
        numbered+=f"{i} {line}"

    has_more=(start_line-1+read_lines)<total_lines

    return {"result":numbered,"total_lines":total_lines,"has_more":has_more}


def write_file(path: str, content: str) -> dict:

    try:
        file_path=resolve_path(path)
        with open(file_path,"w") as handle:
            handle.write(content)
        num_lines = content.count("\n") + 1 if content else 0
        return {"result": f"Wrote {num_lines} lines to {path}"}
    
    except Exception as e:
        return {"error":str(e)}


def edit_file(path: str,operation: str,start_line: int,end_line: int | None = None,content: str | None = None,) -> dict:
    try:
        file_path=resolve_path(path)
        with open(file_path,"r+") as handle:
            result=""
            new_content=""
            old_content_lines=handle.readlines()

            if (operation=="replace"):
                old_tracker=0       #tracker for old content
                new_tracker=0       #tracker for new content
                while (old_tracker<start_line-2):       #storing all the lines before start_line-1
                    new_content+=old_content_lines[old_tracker]
                    old_tracker+=1
                if (start_line>=2):
                    old_tracker=start_line-2
                    new_tracker=start_line-2
                    new_content+=old_content_lines[old_tracker]
                    result+=f" {new_tracker+1}: {old_content_lines[old_tracker]}"
                old_tracker=start_line-1
                new_tracker=start_line-1
                while (old_tracker<end_line):
                    result+=f" -{new_tracker+1}: {old_content_lines[old_tracker]}"
                    old_tracker+=1
                    new_tracker+=1
                new_tracker=start_line-1
                content_lines=content.split("\n")
                for line in content_lines:
                    new_content+=line+"\n"
                    result+=f" +{new_tracker+1}: {line}"
                    new_tracker+=1
                if (old_tracker<len(old_content_lines)):
                    result+=f" {new_tracker+1}: {old_content_lines[old_tracker]}"
                while (old_tracker<len(old_content_lines)):
                    new_content+=old_content_lines[old_tracker]
                    old_tracker+=1

            if (operation=="delete"):
                old_tracker=0
                new_tracker=0
                while (old_tracker<start_line-2):       #storing all the lines before start_line-1
                    new_content+=old_content_lines[old_tracker]
                    old_tracker+=1
                if (start_line>=2):
                    old_tracker=start_line-2
                    new_tracker=start_line-2
                    new_content+=old_content_lines[old_tracker]
                    result+=f" {new_tracker+1}: {old_content_lines[old_tracker]}"
                old_tracker=start_line-1
                new_tracker=start_line-1
                while (old_tracker<end_line):
                    result+=f" -{new_tracker+1}: {old_content_lines[old_tracker]}"
                    old_tracker+=1
                    new_tracker+=1
                if (old_tracker<len(old_content_lines)):
                    result+=f" {new_tracker+1}: {old_content_lines[old_tracker]}"
                while (old_tracker<len(old_content_lines)):
                    new_content+=old_content_lines[old_tracker]
                    old_tracker+=1
            
            if (operation=="append"):
                old_tracker=0
                new_tracker=0
                while (old_tracker<start_line-1):       #storing all the lines before start_line
                    new_content+=old_content_lines[old_tracker]
                    old_tracker+=1
                if (start_line>=1):
                    old_tracker=start_line-1
                    new_tracker=start_line-1
                    new_content+=old_content_lines[old_tracker]
                    result+=f" {new_tracker+1}: {old_content_lines[old_tracker]}"
                old_tracker=start_line
                new_tracker=start_line
                content_lines=content.split("\n")
                for line in content_lines:
                    new_content+=line+"\n"
                    result+=f" +{new_tracker+1}: {line}"
                    new_tracker+=1
                if (old_tracker<len(old_content_lines)):
                    result+=f" {new_tracker+1}: {old_content_lines[old_tracker]}"
                while (old_tracker<len(old_content_lines)):
                    new_content+=old_content_lines[old_tracker]
                    old_tracker+=1
            
            handle.seek(0)
            handle.truncate()
            handle.write(new_content)
        
        return {"result":result}
    
    except ValueError as e:
        return {"error":str(e)}
    
    except FileNotFoundError as e:
        return {"error":str(e)}
    
    except Exception as e:
        return {"error":str(e)}
    

def list_files(path: str = ".", pattern: str = "*") -> dict:
    try:
        full_path = resolve_path(path)
        full_pattern = os.path.join(full_path, pattern)
        matches = glob_module.glob(full_pattern)
        relative_matches = [os.path.relpath(m, WORKSPACE_ROOT) for m in matches]
        return {"result": relative_matches}
    except ValueError as e:
        return {"error": str(e)}