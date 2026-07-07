import os
import subprocess
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "box_insert.html")
    combined_path = os.path.join(script_dir, "combined_print.html")
    output_pdf = os.path.join(script_dir, "Prometheus_82_Box_Insert_and_Positioning_Guide.pdf")
    
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        sys.exit(1)
        
    # Read the original HTML
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # We want to inject the page break and the second page (positioning guide image)
    # right before the closing </body> tag.
    
    second_page_html = """
  <!-- Page Break and Positioning Guide for Double-sided Printing -->
  <div class="page-break"></div>
  <div class="guide-container">
    <img src="P82 Positioning Guide.png" alt="P82 Positioning Guide" />
  </div>
    """
    
    # We also need to inject CSS styles to handle page break and image sizing.
    # Let's locate the closing </style> tag.
    css_injection = """
    /* Print styles for positioning guide */
    .page-break {
      page-break-before: always;
      break-before: page;
    }
    .guide-container {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 100%;
      height: 100%;
      box-sizing: border-box;
      background: #fff;
    }
    .guide-container img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
      margin: 0 auto;
    }
    
    @media print {
      .guide-container {
        page-break-inside: avoid;
        break-inside: avoid;
      }
      .guide-container img {
        max-height: 270mm; /* Fit to A4 height minus margins */
      }
    }
    """
    
    if "</style>" in html_content:
        html_content = html_content.replace("</style>", css_injection + "\n  </style>")
    else:
        # Fallback if no style tag
        html_content = html_content.replace("</head>", f"<style>{css_injection}</style>\n</head>")
        
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", second_page_html + "\n</body>")
    else:
        html_content += second_page_html
        
    # Write to combined_print.html
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Created temporary print HTML at: {combined_path}")
    
    # Find Google Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")
    ]
    
    chrome_bin = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_bin = path
            break
            
    if not chrome_bin:
        print("Error: Google Chrome executable not found. Please install Chrome or modify this script with your browser path.")
        sys.exit(1)
        
    print(f"Using Chrome at: {chrome_bin}")
    
    # Run Chrome in headless mode to generate the PDF
    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf}",
        combined_path
    ]
    
    print("Generating PDF...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Successfully generated PDF: {output_pdf}")
    except subprocess.CalledProcessError as e:
        print("Error during PDF generation:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)
    finally:
        # Clean up temporary HTML file
        if os.path.exists(combined_path):
            os.remove(combined_path)
            print("Cleaned up temporary HTML file.")

if __name__ == "__main__":
    main()
