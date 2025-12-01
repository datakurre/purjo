---
layout: default
title: Advanced Use Cases
---

# Advanced use cases

This section covers more advanced scenarios and capabilities when working with `purjo`.

## File I/O within tasks

Tasks often need to interact with the file system, whether it's reading input files, generating reports, or processing documents. `purjo` tasks, being based on Python and Robot Framework, can leverage their respective libraries for file input/output (I/O) operations.

### Example: PDF manipulation

This example illustrates how to perform file I/O operations, specifically creating and merging PDF documents using Python libraries.

#### `PDF.py` (Python library for PDF operations)

```python
from PyPDF2 import PdfReader
from PyPDF2 import PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


class PDF:
    def create_pdf(self, filename: str, message: str):
        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(100, 750, message)
        c.save()

    def merge_pdf(self, a: str, b: str, filename: str):
        pdf_writer = PdfWriter()

        for page in PdfReader(a).pages:
            pdf_writer.add_page(page)

        for page in PdfReader(b).pages:
            pdf_writer.add_page(page)

        with open(filename, "wb") as output_pdf:
            pdf_writer.write(output_pdf)
```

This Python file defines a `PDF` class with methods `create_pdf` to generate a new PDF with text and `merge_pdf` to combine two existing PDF files into one. These methods utilize `PyPDF2` and `reportlab`, which are standard Python libraries for PDF handling.

#### Using in Robot Framework

These Python functions can be exposed as keywords in a Robot Framework file (e.g., `pdf.robot`) and then called from your BPMN process.

```robotframework
*** Settings ***
Library    PDF.py

*** Tasks ***
Generate and Merge Documents
    PDF.Create Pdf    first.pdf    Hello from purjo!
    PDF.Create Pdf    second.pdf   Another page.
    PDF.Merge Pdf     first.pdf    second.pdf    merged.pdf
```

### Considerations for file I/O

*   **File Paths:** When working with file paths, ensure they are relative to your project's root or correctly resolved as absolute paths.
*   **Temporary Files:** For intermediate files, consider using Python's `tempfile` module or Robot Framework's `OperatingSystem` library to create and manage temporary files, ensuring they are cleaned up after use.
*   **Dependencies:** Remember to declare any third-party Python libraries (like `PyPDF2` or `reportlab` in this example) in your `pyproject.toml` or `requirements.txt` so `uv` can install them. You can add them using `uv add`:
    ```console
    $ uv add PyPDF2 reportlab
    ```
*   **Passing Files as Variables:** If you need to pass file contents or file paths between tasks or back to the BPMN engine, consider serializing the content (e.g., base64 encoding for binary files) or passing file paths as string variables.

## Immediate execution with `pur run`

For rapid development and testing, `purjo` provides the `pur run` command. This command combines deployment and execution into a single step.

```console
$ pur run <process.bpmn> [OPTIONS]
```

It performs the following actions:
1.  Deploys the specified BPMN (and DMN/Form) resources to the configured Operaton engine.
2.  Starts a new process instance of the deployed process.
3.  Prints the URL to the Operaton Cockpit for the new instance.

### Options

*   `--variables <json_string_or_file>`: Pass initial process variables. You can provide a JSON string or a path to a JSON file.
*   `--name <deployment_name>`: Set a custom name for the deployment (default: "pur(jo) deployment").
*   `--force`: Force deployment even if resources haven't changed.

### Example

```console
$ pur run hello.bpmn --variables '{"user": "Alice"}'
Started: http://localhost:8080/operaton/app/cockpit/default/#/process-instance/36228e79...
```

## Managing deployments

For more granular control over the deployment lifecycle, you can use the `pur operaton` (or `pur bpm`) subcommands.

### Deploying resources

To deploy resources without starting an instance:

```console
$ pur operaton deploy <file1> <file2> ...
```

This is useful when you have multiple related files (e.g., a BPMN process and a DMN decision table) that should be deployed together.

### Starting processes

To start a process instance from an existing deployment (using its Process Definition Key):

```console
$ pur operaton start <process_key>
```

