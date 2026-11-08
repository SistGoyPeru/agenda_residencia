import pathlib
p=pathlib.Path(r"C:\Users\alexg\OneDrive\Alex_2026\AGENDA PARA TRASNPORTITAS DE REPARTOS\templates\residencias\reporte_mensual.html")
s=p.read_text(encoding="utf-8")
# asegurar target blank
if 'target="_blank"' not in s:
    s=s.replace('">Descargar PDF</a>',' target="_blank">Descargar PDF</a>')
p.write_text(s,encoding="utf-8")
print("ok reporte target blank")
