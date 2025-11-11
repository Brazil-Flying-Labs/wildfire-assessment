# Wildfire Assessment UI

Interface React responsável por interagir com a API do sistema de avaliação de incêndios florestais. A aplicação agora exige autenticação via Auth0 antes de permitir o acesso aos recursos protegidos.

## Pré-requisitos

- Node.js 16+ (recomenda-se a versão suportada pelo projeto)
- Conta e aplicativo registrado no [Auth0](https://auth0.com/) com Refresh Token Rotation habilitado

## Variáveis de ambiente

Crie um arquivo `.env.local` dentro da pasta `ui` com os valores abaixo:

```
REACT_APP_WILDLIFE_API_URL=https://sua-api.example.com
REACT_APP_AUTH0_DOMAIN=example-region.auth0.com
REACT_APP_AUTH0_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_AUTH0_AUDIENCE=https://sua-api.example.com
```

> Observações
>
> - `REACT_APP_WILDLIFE_API_URL` já era utilizada anteriormente e continua obrigatória.
> - O domínio, Client ID e Audience devem corresponder à API configurada no Auth0.
> - O Auth0Provider está configurado com `useRefreshTokens` e `cacheLocation="localstorage"`, portanto a aplicação precisa ter o Refresh Token Rotation habilitado no dashboard do Auth0.

## Scripts

No diretório `ui` execute:

- `npm start` — inicia a aplicação em modo desenvolvimento em `http://localhost:3000`.
- `npm run build` — gera o bundle minificado para produção em `ui/build`.
- `npm test` — executa a suíte de testes padrão do Create React App.

## Fluxo de autenticação

- Usuários não autenticados são imediatamente redirecionados para o Auth0.
- Após o login, cada chamada à API (`/ecological_reserve/` e `/analyze/`) envia o header `Authorization: Bearer <token>` obtido via `getAccessTokenSilently`.
- O uso de refresh tokens garante que a sessão permaneça válida sem exigir novas interações do usuário até que o Auth0 determine o contrário.

Caso algum dos parâmetros do Auth0 não esteja configurado, a interface exibirá uma mensagem informando o problema em vez de iniciar normalmente.
