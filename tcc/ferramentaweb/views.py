import openai
import json
from django.http import JsonResponse
from django.shortcuts import render

openai.api_key = ''
# ferramentaweb/views.py

def index(request):
    return render(request, 'ferramentaweb/index.html')

def gerar_caso(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '')

            # Lista de palavras-chave relacionadas ao tema do TCC
            keywords = ['psicopatologia', 'sintomas', 'diagnóstico', 'tratamento', 'transtorno', 'depressão', 'ansiedade', 'casos', 'clínico']

            # Verificando se a entrada do usuário contém palavras-chave relevantes
            if not any(keyword in user_input.lower() for keyword in keywords):
                return JsonResponse({'error': 'Sua pergunta deve ser relevante ao tema de psicopatologia.'})

            # Continuar com a geração de caso se a entrada for relevante
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um especialista em psicopatologia. Responda apenas dentro deste contexto."},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            
            chat_response = response['choices'][0]['message']['content']
            return JsonResponse({'response': chat_response})

        except Exception as e:
            return JsonResponse({'error': str(e)})
