# Money Play — configuração de produção

Este pacote remove a ativação automática/demonstrativa do VIP.

## VIP no Google Play
Como o VIP libera funcionalidades/conteúdo dentro do aplicativo, a versão distribuída pela Google Play deve ser configurada de acordo com as regras atuais de cobrança do Google Play.

Crie dois produtos de assinatura no Play Console:
- `moneyplay_vip_ouro`
- `moneyplay_vip_diamante`

Os IDs precisam ser exatamente os mesmos usados no aplicativo Android.

## O que ainda depende da sua conta
1. Conta Google Play Console e verificação.
2. Criar os produtos de assinatura.
3. Configurar a conta de pagamentos/merchant.
4. Publicar o backend em HTTPS com domínio.
5. Configurar a verificação server-side das compras.
6. Assinar o Android App Bundle com a chave de assinatura do aplicativo.

Não coloque chaves privadas, service-account JSON ou senhas dentro deste ZIP.
