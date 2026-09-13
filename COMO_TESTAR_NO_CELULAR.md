# Money Play — teste pelo celular

Este pacote foi preparado para gerar automaticamente um APK de teste pelo GitHub Actions, sem precisar instalar Android Studio no celular.

## Passo a passo

1. Crie uma conta no GitHub.
2. Crie um repositório novo, por exemplo `MoneyPlay`.
3. Envie **todo o conteúdo deste ZIP** para o repositório, mantendo as pastas `android`, `backend` e `.github`.
4. Abra a aba **Actions** do repositório.
5. Entre em **Build Money Play APK**.
6. Toque em **Run workflow**.
7. Quando terminar, abra a execução concluída e baixe o artefato **MoneyPlay-apk-teste**.
8. Extraia o APK e instale no Android para testar.

## Importante

O APK de teste ainda precisa de um endereço HTTPS real do backend. No código Android, o endereço atual é um placeholder (`SEU-DOMINIO-DE-PRODUCAO.example`). Portanto, para o app funcionar de verdade, o backend Flask precisa ser publicado primeiro e esse endereço precisa ser colocado em `MainActivity.kt`.

Este pacote não deve ser tratado como versão final da Google Play ainda. Antes da publicação é necessário, entre outras coisas, backend HTTPS em produção, assinatura de release/AAB, política de privacidade, segurança de autenticação, upload real de prints e revisão das regras de pagamento/VIP e recompensas da Google Play.
