# tasks_app/models.py
class UploadedImage(models.Model):
    image = models.ImageField(upload_to='uploads/')
    classification_result = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


# tasks_app/forms.py
class UploadedImageForm(forms.ModelForm):
    class Meta:
        model = UploadedImage
        fields = ['image']


# tasks_app/tasks.py
from PIL import Image, ImageChops
from celery import shared_task
from .models import UploadedImage


@shared_task
def classify_uploaded_image(image_id):
    uploaded_image = UploadedImage.objects.get(pk=image_id)
    with Image.open(uploaded_image.image.path) as image:
        width, height = image.size
        rgb_image = image.convert('RGB')
        red, green, blue = rgb_image.split()
        grayscale = (
            image.mode in ('1', 'L', 'LA')
            or ImageChops.difference(red, green).getbbox() is None
            and ImageChops.difference(red, blue).getbbox() is None
        )
    kind = 'grayscale' if grayscale else 'color'
    uploaded_image.classification_result = f'{kind}, {width}x{height}'
    uploaded_image.save(update_fields=['classification_result'])
    return uploaded_image.classification_result


# tasks_app/views.py
def upload_image(request):
    form = UploadedImageForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        uploaded_image = form.save()
        task = classify_uploaded_image.delay(uploaded_image.id)
        return HttpResponse(f'Obraz przeslany. image_id={uploaded_image.id}, task_id={task.id}')
    return render(request, 'tasks_app/upload_image.html', {'form': form})


# templates/tasks_app/upload_image.html
"""
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Prześlij obraz</button>
</form>
"""


