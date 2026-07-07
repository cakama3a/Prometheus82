import os
import subprocess
import sys

def run_chrome_pdf(chrome_bin, input_html, output_pdf):
    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf}",
        input_html
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Successfully generated PDF: {output_pdf}")
    except subprocess.CalledProcessError as e:
        print(f"Error generating PDF {output_pdf}:")
        print(e.stdout)
        print(e.stderr)
        sys.exit(1)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "box_insert.html")
    combined_path = os.path.join(script_dir, "combined_print.html")
    combined_halftone_path = os.path.join(script_dir, "combined_print_halftone.html")
    
    output_pdf = os.path.join(script_dir, "Prometheus_82_Box_Insert_and_Positioning_Guide.pdf")
    output_pdf_halftone = os.path.join(script_dir, "Prometheus_82_Box_Insert_and_Positioning_Guide_Halftone.pdf")
    
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        sys.exit(1)
        
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
        print("Error: Google Chrome executable not found. Please install Chrome.")
        sys.exit(1)
        
    print(f"Using Chrome at: {chrome_bin}")

    # Read the original HTML
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Standard styles & page structure
    second_page_html = """
  <!-- Page Break and Positioning Guide for Double-sided Printing -->
  <div class="page-break"></div>
  <div class="guide-container">
    <img src="P82 Positioning Guide.png" alt="P82 Positioning Guide" />
  </div>
    """
    
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
    
    # Construct base HTML
    base_html = html_content
    if "</style>" in base_html:
        base_html = base_html.replace("</style>", css_injection + "\n  </style>")
    else:
        base_html = base_html.replace("</head>", f"<style>{css_injection}</style>\n</head>")
        
    if "</body>" in base_html:
        base_html = base_html.replace("</body>", second_page_html + "\n</body>")
    else:
        base_html += second_page_html

    # --- 1. Standard PDF ---
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(base_html)
    
    print("Generating standard PDF...")
    run_chrome_pdf(chrome_bin, combined_path, output_pdf)
    
    # --- 2. Halftone PDF (Ink-Saving dots) ---
    halftone_css = """
    /* Halftone Effect */
    .sheet, .guide-container {
      position: relative;
    }
    .halftone-overlay {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 99999;
      background-image: radial-gradient(circle, #ffffff 0.7px, transparent 0.8px);
      background-size: 2.2px 2.2px;
    }
    @media print {
      .halftone-overlay {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
    }
    """
    
    # Inject halftone CSS
    halftone_html = base_html
    if "</style>" in halftone_html:
        halftone_html = halftone_html.replace("</style>", halftone_css + "\n  </style>")
    
    # Inject halftone overlay divs
    # Insert inside <main class="sheet">
    halftone_html = halftone_html.replace('<main class="sheet">', '<main class="sheet"><div class="halftone-overlay"></div>')
    # Insert inside <div class="guide-container">
    halftone_html = halftone_html.replace('<div class="guide-container">', '<div class="guide-container"><div class="halftone-overlay"></div>')
    
    with open(combined_halftone_path, "w", encoding="utf-8") as f:
        f.write(halftone_html)
        
    print("Generating Halftone (ink-saving) PDF...")
    run_chrome_pdf(chrome_bin, combined_halftone_path, output_pdf_halftone)
    
    # Cleanup
    for p in (combined_path, combined_halftone_path):
        if os.path.exists(p):
            os.remove(p)

if __name__ == "__main__":
    main()
