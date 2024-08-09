import openai
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

openai.api_key = os.getenv('"OPENAI')

def index(request):
    return render(request, 'ferramentaweb/index.html')

def gerar_caso(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input')

        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=user_input,
                max_tokens=150,
                n=1,
                stop=None,
                temperature=0.7,
            )

            generated_text = response.choices[0].text.strip()
            return JsonResponse({'response': generated_text})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=405)
