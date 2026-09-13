# Money Play — versão funcional

## Rodar no computador
1. Instale Python 3.11+.
2. `pip install -r requirements.txt`
3. Linux/macOS: `export ADMIN_PASSWORD="uma-senha-forte"`; Windows PowerShell: `$env:ADMIN_PASSWORD="uma-senha-forte"`
4. `python app.py`
5. Abra `http://localhost:5000`

## O que já funciona
- Cadastro e login
- Tarefas normais e VIP
- Limite de 2 envios por tarefa
- Aprovação/rejeição pelo ADM
- Moedas liberadas somente após aprovação
- Carteira
- Chave Pix: celular, e-mail ou aleatória (sem CPF)
- Solicitação de saque de R$2/R$5/R$10/R$20
- Histórico de saques
- VIP Ouro e Diamante
- Mais tarefas para VIP e prioridade de saque como regra de produto
- Banir/desbanir usuários
- Criação de tarefas no ADM
- Layout responsivo inspirado na prévia aprovada

## Importante antes da Google Play
O projeto é funcional como aplicação web, mas pagamentos reais e publicação exigem infraestrutura de produção:
- banco PostgreSQL/Supabase ou equivalente;
- HTTPS e domínio;
- hash de senhas (esta versão de demonstração usa armazenamento simples e NÃO deve ser publicada assim);
- gateway de pagamento para cobrar VIP;
- provedor/integração de pagamentos Pix para processar saques;
- armazenamento seguro de comprovantes;
- política de privacidade, termos e adequação às regras da Google Play.

A ativação do VIP neste pacote é demonstrativa até o webhook do gateway ser conectado. Os saques são registrados como pendentes para o ADM; não existe transferência Pix automática sem um provedor configurado.


## Pagamentos manuais
Nesta versão, os saques são pagos manualmente pelo administrador:
1. O usuário solicita o saque.
2. O pedido aparece no ADM com valor e chave Pix.
3. O administrador faz o Pix pelo próprio banco.
4. Depois clica em "Marcar como pago".
5. Se precisar cancelar um pedido pendente, o ADM pode clicar em "Cancelar"; as moedas reservadas retornam ao usuário.

Os pagamentos não são automáticos nesta versão.
