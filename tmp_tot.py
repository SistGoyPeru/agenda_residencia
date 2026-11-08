import pathlib
p=pathlib.Path(r"C:\Users\alexg\OneDrive\Alex_2026\AGENDA PARA TRASNPORTITAS DE REPARTOS\residencias\views.py")
s=p.read_text(encoding="utf-8")
old='''          <tfoot>
            <tr>
              <td colspan="4">Totales</td>
              <td class="num">{{ total_unidades }}</td>
              <td class="num">{{ total_cupones }}</td>
            </tr>
          </tfoot>'''
new='''          <tfoot>
            <tr>
              <td colspan="4"><strong>Totales</strong></td>
              <td class="num"><strong>{{ total_visitas }}</strong></td>
              <td class="num"><strong>{{ total_unidades }}</strong></td>
              <td class="num"><strong>{{ total_cupones }}</strong></td>
            </tr>
          </tfoot>'''
if old in s:
    s=s.replace(old,new,1)
    p.write_text(s,encoding="utf-8")
    print("ok totales pdf")
else:
    print("NO MATCH tfoot")
    import re
    for m in re.finditer(r'<tfoot>.*?</tfoot>', s, re.S):
        print(repr(m.group(0))[:300])
