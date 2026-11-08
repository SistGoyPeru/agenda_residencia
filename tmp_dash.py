import pathlib
p=pathlib.Path(r"C:\Users\alexg\OneDrive\Alex_2026\AGENDA PARA TRASNPORTITAS DE REPARTOS\templates\residencias\dashboard.html")
s=p.read_text(encoding="utf-8")
old='<a class="boton boton-mini boton-fantasma" href="{% url ' + "'" + 'reporte_mensual' + "'" + ' %}">Informe</a>'
new='<a class="boton boton-mini boton-fantasma" href="{% url ' + "'" + 'reporte_mensual_pdf' + "'" + ' %}" target="_blank">Informe PDF</a>'
if old in s:
    s=s.replace(old,new,1)
    p.write_text(s,encoding="utf-8")
    print("ok dashboard informe -> pdf")
else:
    print("NO MATCH dashboard")
    # mostrar contexto
    import re
    for m in re.finditer(r'reporte_mensual', s):
        print(m.group(0))
