import json, uuid, openai
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from .models import ConversationHistory

openai.api_key = ''  # Substitua com sua chave da API

# Armazenar o histórico da conversa na sessão
def index(request):
    if 'chat_history' not in request.session:
        request.session['chat_history'] = [
            {"role": "system", "content": "Você é um especialista em psicopatologia. Responda de forma útil e apropriada com base no contexto de psicopatologia."}
        ]

    # Gera um ID único para o usuário, se não existir
    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())  # ou use um simples contador/incremento

    context = {
        'user_id': request.session['user_id'],
    }

    return render(request, 'ferramentaweb/index.html', context)

def gerar_caso_stream(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '')

            # Recupera o histórico de conversa da sessão
            chat_history = request.session.get('chat_history', [])
            print(f"Histórico anterior: {chat_history}")

            # Adiciona a mensagem do usuário ao histórico
            chat_history.append({"role": "user", "content": user_input})
            print(f"Histórico atualizado: {chat_history}")

            # Função de streaming para gerar a resposta
            def stream_response():
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=chat_history,
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
                print(f"Histórico final: {chat_history}")

                # Salva o histórico atualizado na sessão
                request.session['chat_history'] = chat_history
                request.session.modified = True

                yield json.dumps({"response": accumulated_text}) + "\n"

            return StreamingHttpResponse(stream_response(), content_type='application/json')

        except Exception as e:
            return StreamingHttpResponse(
                json.dumps({'error': str(e)}), 
                content_type='application/json'
            )
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)
    
def process_message(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id', '')
        message = request.POST.get('message')

        if user_id is None or user_id.strip() == "":
            return JsonResponse({'error': 'User ID é obrigatório.'}, status=400)

        # Salvar mensagem no histórico
        ConversationHistory.objects.create(user_id=user_id, message=message)

        # Processar a mensagem e gerar uma resposta
        response = process_user_message(message)  # Supondo que você tem uma função para processar a mensagem

        return JsonResponse({'response': response})


def get_history(request):
    user_id = request.GET.get('user_id', '')
    print(f"Recebido user_id: {user_id}")  # Adicione isto para depuração

    if not user_id:
        return JsonResponse({'error': 'ID do usuário não fornecido'}, status=400)

    # Obtemos o histórico da sessão
    chat_history = request.session.get('chat_history', [])
    print(f"Histórico da sessão: {chat_history}")  # Adicione isto para depuração

    return JsonResponse(chat_history, safe=False)
