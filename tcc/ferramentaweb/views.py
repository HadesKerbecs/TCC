import json, uuid, openai
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from .models import Historico_Conversa
from django.utils import timezone

openai.api_key = ''

def index(request):
    if 'chat_historico' not in request.session:
        request.session['chat_historico'] = [
            {"role": "system", "content": "Você é um especialista em psicopatologia. Responda de forma útil e apropriada com base no contexto de psicopatologia."}
        ]

    if 'user_id' not in request.session:
        request.session['user_id'] = str(uuid.uuid4())

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
            chat_historico = request.session.get('chat_historico', [])
            print(f"Histórico anterior: {chat_historico}")

            # Adiciona a mensagem do usuário ao histórico
            chat_historico.append({"role": "user", "content": user_input})
            print(f"Histórico atualizado: {chat_historico}")

            # Recupera a personalização da sessão, se houver
            personalizacao = request.session.get('personalizacao', {})
            if personalizacao:
                nivel_complexidade = personalizacao.get('nivel_complexidade', None)
                if nivel_complexidade:
                    chat_historico.append({
                        "role": "system", 
                        "content": f"Personalização aplicada: {personalizacao}"
                    })

            if len(chat_historico) > 50:
                chat_historico = chat_historico[10:]
                print(f"Histórico truncado: {chat_historico}")

            # Função de streaming para gerar a resposta
            def stream_response():
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=chat_historico,
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
                chat_historico.append({"role": "assistant", "content": accumulated_text})
                print(f"Histórico final: {chat_historico}")

                # Salva o histórico atualizado na sessão
                request.session['chat_historico'] = chat_historico
                request.session.modified = True

                # Salva o histórico no banco de dados
                try:

                    Historico_Conversa.objects.create(
                        user_id=request.session['user_id'],
                        message=user_input,
                        response=accumulated_text,
                        timestamp=timezone.now()
                    )
                except Exception as e:
                    print(f"Erro ao salvar histórico no banco de dados: {e}")

                yield json.dumps({"response": accumulated_text}) + "\n"

            return StreamingHttpResponse(stream_response(), content_type='application/json')
        except Exception as e:
            return StreamingHttpResponse(
                json.dumps({'error': str(e)}),
                content_type='application/json'
            )
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

def processo_user_menssagem(message):
    response = f"Você disse: {message}"
    return response

def processar_mensagem(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id', '').strip()
        message = request.POST.get('message', '').strip()

        print(f"Recebido user_id: {user_id}")
        print(f"Recebida mensagem: {message}")

        if not user_id:
            return JsonResponse({'error': 'User ID é obrigatório.'}, status=400)
        if not message:
            return JsonResponse({'error': 'Mensagem é obrigatória.'}, status=400)

        try:
            historico = Historico_Conversa.objects.create(user_id=user_id, message=message)
            print(f"Histórico salvo: {historico}")

            response = processo_user_menssagem(message)

            return JsonResponse({'response': response})
        except Exception as e:
            print(f"Erro ao salvar no banco de dados: {e}")
            return JsonResponse({'error': 'Erro ao processar a mensagem.'}, status=500)
    else:
        return JsonResponse({'error': 'Método não permitido.'}, status=405)

def salvar_historico(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # Capturando o corpo da requisição
            user_id = data.get('user_id')
            message = data.get('message')
            response = data.get('response')

            if user_id and message and response:
                Historico_Conversa.objects.create(
                    user_id=user_id, 
                    message=message, 
                    response=response
                )
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Dados incompletos'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

def pegar_historico(request):
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse([], safe=False)

    try:
        historico = Historico_Conversa.objects.filter(user_id=user_id).order_by('timestamp')
        
        # Formatar os dados de maneira organizada
        dados_formatados = []
        for item in historico:
            formatted_entry = {
                'message': item.message.replace('\n', '<br>'),  # Substitui quebras de linha
                'response': item.response.replace('\n', '<br>'),
                'timestamp': item.timestamp.strftime('%d/%m/%Y %H:%M'),  # Formatação do timestamp
                'user_id': item.user_id  # Inclui o user_id, se necessário
            }
            dados_formatados.append(formatted_entry)

        return JsonResponse(dados_formatados, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def personalizar_caso(request):
    if request.method == 'POST':
        try:
            # Verifique se o tipo de conteúdo é JSON
            if request.content_type != 'application/json':
                return JsonResponse({'error': 'Tipo de conteúdo inválido. Esperado application/json.'}, status=400)
            
            # Extrair os dados de personalização enviados pelo formulário
            data = json.loads(request.body)
            idade = data.get('idade')
            sexo = data.get('sexo')
            historico_medico = data.get('historico_medico')
            contexto_social = data.get('contexto_social')
            nivel_complexidade = data.get('nivel_complexidade')

            # Verificar se os campos obrigatórios foram enviados
            if not all([idade, sexo, historico_medico, contexto_social, nivel_complexidade]):
                return JsonResponse({'error': 'Todos os campos de personalização são obrigatórios.'}, status=400)

            # Validar dados (exemplo: idade deve ser um número)
            try:
                idade = int(idade)
            except ValueError:
                return JsonResponse({'error': 'Idade deve ser um número válido.'}, status=400)

            # Armazenar os dados de personalização na sessão
            request.session['personalizacao'] = {
                'idade': idade,
                'sexo': sexo,
                'historico_medico': historico_medico,
                'contexto_social': contexto_social,
                'nivel_complexidade': nivel_complexidade
            }

            return JsonResponse({'message': 'Personalização aplicada com sucesso.'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Falha ao decodificar o JSON enviado.'}, status=400)

    # Retornar erro se não for POST
    return JsonResponse({'error': 'Método não permitido. Use POST.'}, status=405)

def resetar_personalizacao(request):
    if request.method == 'POST':
        # Remove a personalização da sessão
        if 'personalizacao' in request.session:
            del request.session['personalizacao']
            request.session.modified = True
            return JsonResponse({'message': 'Personalização resetada com sucesso.'})
        return JsonResponse({'message': 'Nenhuma personalização encontrada para resetar.'})
    return JsonResponse({'error': 'Método não permitido.'}, status=405)

def obter_dados_personalizacao(request):
    if request.method == 'GET':
        personalizacao = request.session.get('personalizacao', {})
        return JsonResponse({'personalizacao': personalizacao})
    return JsonResponse({'error': 'Método não permitido.'}, status=405)
