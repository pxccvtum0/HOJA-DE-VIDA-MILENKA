import io
import requests
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from pypdf import PdfWriter, PdfReader 

from Perfil.models import (
    DatosPersonales, ExperienciaLaboral, 
    CursosRealizados, Reconocimientos, 
    ProductosAcademicos, ProductosLaborales, VentaGarage
)

def get_active_profile():
    return DatosPersonales.objects.filter(perfilactivo=1).first()

def home(request):
    perfil = get_active_profile()
    if not perfil: return render(request, 'home.html', {'perfil': None})
    context = {
        'perfil': perfil,
        'resumen_exp': ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_cursos': CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_rec': Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_acad': ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_lab': ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True)[:3],
        'resumen_garage': VentaGarage.objects.all()[:5],
    }
    return render(request, 'home.html', context)

# Vistas estándar
def experiencia(request): return render(request, 'experiencia.html', {'datos': ExperienciaLaboral.objects.all(), 'perfil': get_active_profile()})
def productos_academicos(request): return render(request, 'productos_academicos.html', {'datos': ProductosAcademicos.objects.all(), 'perfil': get_active_profile()})
def productos_laborales(request): return render(request, 'productos_laborales.html', {'datos': ProductosLaborales.objects.all(), 'perfil': get_active_profile()})
def cursos(request): return render(request, 'cursos.html', {'datos': CursosRealizados.objects.all(), 'perfil': get_active_profile()})
def reconocimientos(request): return render(request, 'reconocimientos.html', {'datos': Reconocimientos.objects.all(), 'perfil': get_active_profile()})
def garage(request): return render(request, 'garage.html', {'datos': VentaGarage.objects.all(), 'perfil': get_active_profile()})

def pdf_datos_personales(request):
    perfil = get_object_or_404(DatosPersonales, perfilactivo=1)

    incl_exp = request.GET.get('exp') == 'true'
    incl_cursos = request.GET.get('cursos') == 'true'
    incl_logros = request.GET.get('logros') == 'true'
    incl_proy = request.GET.get('proy') == 'true'
    incl_garage = request.GET.get('garage') == 'true'

    experiencias = ExperienciaLaboral.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if incl_exp else []
    cursos_objs = CursosRealizados.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if incl_cursos else []
    reco_objs = Reconocimientos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if incl_logros else []
    garage_items = VentaGarage.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if incl_garage else []
    
    academicos = ProductosAcademicos.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if incl_proy else []
    laborales = ProductosLaborales.objects.filter(idperfilconqueestaactivo=perfil, activarparaqueseveaenfront=True) if incl_proy else []

    template = get_template('cv_pdf_maestro.html')
    html = template.render({
        'perfil': perfil, 
        'items': experiencias, 
        'productos': academicos,
        'productos_laborales': laborales, 
        'cursos': cursos_objs, 
        'reconocimientos': reco_objs,
        'garage': garage_items,
        'incl_experiencia': incl_exp,
        'incl_proyectos': incl_proy,
        'incl_cursos': incl_cursos,
        'incl_logros': incl_logros,
        'incl_garage': incl_garage
    })
    
    buffer_cv = io.BytesIO()
    pisa.CreatePDF(io.BytesIO(html.encode("UTF-8")), dest=buffer_cv)

    writer = PdfWriter()
    buffer_cv.seek(0)
    try:
        reader_base = PdfReader(buffer_cv)
        for page in reader_base.pages:
            writer.add_page(page)
    except:
        pass

    def pegar_certificados(queryset, nombre_campo):
        for obj in queryset:
            archivo = getattr(obj, nombre_campo, None)
            if archivo and hasattr(archivo, 'url'):
                try:
                    r = requests.get(archivo.url, timeout=15)
                    if r.status_code == 200:

                        writer.append(io.BytesIO(r.content))
                except Exception as e:
                    print(f"Error pegando: {e}")
                    continue

    if incl_exp: pegar_certificados(experiencias, 'rutacertificado')
    if incl_cursos: pegar_certificados(cursos_objs, 'rutacertificado')
    if incl_logros: pegar_certificados(reco_objs, 'rutacertificado')
    
    if incl_garage: 
        pegar_certificados(garage_items, 'documento_interes')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Portafolio_{perfil.apellidos}.pdf"'
    writer.write(response)
    writer.close()
    
    return response