import openai
import json
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render

openai.api_key = ''  # Substitua com sua chave da API

# Armazenar o histórico da conversa na sessão
def index(request):
    # Limpa o histórico de conversa ao carregar a página pela primeira vez
    request.session['chat_history'] = [
        {"role": "system", "content": "Você é um especialista em psicopatologia. Responda de forma útil e apropriada com base no contexto de psicopatologia."}
    ]
    return render(request, 'ferramentaweb/index.html')

def gerar_caso_stream(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '')

            # Recupera o histórico de conversa da sessão
            chat_history = request.session.get('chat_history', [])

            # Adiciona a mensagem do usuário ao histórico
            chat_history.append({"role": "user", "content": user_input})

            # Função de streaming para gerar a resposta
            def stream_response():
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=chat_history,  # Envia todo o histórico da conversa
                    max_tokens=1000,
                    temperature=0.7,
                    stream=True
                )

                accumulated_text = ''
                for chunk in response:
                    if 'choices' in chunk:
                        choice = chunk['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            content = choice['delta']['content']
                            if content:
                                accumulated_text += content
                                yield json.dumps({"response": accumulated_text}) + "\n"
                    if 'error' in chunk:
                        yield json.dumps({'error': chunk['error']['message']}) + "\n"

                # Adiciona a resposta do modelo ao histórico
                chat_history.append({"role": "assistant", "content": accumulated_text})

                # Salva o histórico atualizado na sessão
                request.session['chat_history'] = chat_history

                yield json.dumps({"response": accumulated_text}) + "\n"

            return StreamingHttpResponse(stream_response(), content_type='application/json')
        except Exception as e:
            return StreamingHttpResponse(
                json.dumps({'error': str(e)}), 
                content_type='application/json'
            )
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)
