# Deploy no EasyPanel

Guia completo para fazer deploy do Gerador de Relatórios Kiro no EasyPanel.

## 📋 Pré-requisitos

1. Conta no [EasyPanel](https://easypanel.io/)
2. Servidor configurado no EasyPanel
3. Chave API da OpenAI
4. (Opcional) Chave API do MiniMax para modelo gratuito

## 🚀 Deploy Rápido

### Opção 1: Deploy via GitHub (Recomendado)

1. **Push do código para GitHub**

   ```bash
   git add .
   git commit -m "feat: prepare for EasyPanel deployment"
   git push origin main
   ```

2. **Criar aplicação no EasyPanel**
   - Acesse seu painel do EasyPanel
   - Clique em "Create Application"
   - Selecione "GitHub Repository"
   - Conecte seu repositório
   - Selecione a branch `main`

3. **Configurar Build**
   - Build Method: `Dockerfile`
   - Dockerfile Path: `Dockerfile`
   - Context: `.` (raiz do projeto)

4. **Configurar Variáveis de Ambiente**

   Variáveis obrigatórias:

   ```
   OPENAI_API_KEY=sk-your-key-here
   SECRET_KEY=your-secret-key-min-32-chars
   DATABASE_URL=postgresql://user:pass@host:5432/db
   REDIS_URL=redis://host:6379/0
   ```

5. **Deploy**
   - Clique em "Deploy"
   - Aguarde o build (5-10 minutos)
   - Acesse sua aplicação!

### Opção 2: Deploy via Docker Image

1. **Build da imagem localmente**

   ```bash
   docker build -t gerador-relatorio-kiro:latest .
   ```

2. **Push para registry**

   ```bash
   docker tag gerador-relatorio-kiro:latest your-registry/gerador-relatorio-kiro:latest
   docker push your-registry/gerador-relatorio-kiro:latest
   ```

3. **Deploy no EasyPanel**
   - Create Application → Docker Image
   - Image: `your-registry/gerador-relatorio-kiro:latest`
   - Configure variáveis de ambiente
   - Deploy

## ⚙️ Configuração Detalhada

### 1. Variáveis de Ambiente

#### Obrigatórias

```bash
# OpenAI API Key (obrigatório)
OPENAI_API_KEY=sk-proj-...

# Secret Key para JWT (mínimo 32 caracteres)
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars

# Database URL (use addon PostgreSQL do EasyPanel)
DATABASE_URL=postgresql://user:password@postgres:5432/relatorio_db

# Redis URL (use addon Redis do EasyPanel)
REDIS_URL=redis://redis:6379/0
```

#### Opcionais - Otimização de Custos

```bash
# MiniMax API Key (modelo gratuito)
MINIMAX_API_KEY=your-minimax-key

# Estratégia de seleção de modelo
MODEL_SELECTION_STRATEGY=auto  # auto, simple, complex

# Modelos a usar
SIMPLE_MODEL=minimax-m2.5
COMPLEX_MODEL=gpt-4o
```

#### Opcionais - Configuração

```bash
# Aplicação
APP_NAME=gerador_relatorio_kiro
ENVIRONMENT=production
LOG_LEVEL=INFO

# Segurança
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
ENABLE_SECURITY_GUARD=true
ENABLE_PROMPT_INJECTION_DETECTION=true

# Upload
MAX_UPLOAD_SIZE_MB=50
ALLOWED_EXTENSIONS=.pdf,.docx,.xlsx,.csv,.txt,.pptx,.md

# Storage
STORAGE_TYPE=local
STORAGE_LOCAL_PATH=/app/uploads

# Features
MAX_REVISION_ATTEMPTS=3
```

### 2. Addons Recomendados

#### PostgreSQL

- Vá em "Addons" → "Add PostgreSQL"
- Copie a `DATABASE_URL` gerada
- Cole nas variáveis de ambiente da aplicação

#### Redis

- Vá em "Addons" → "Add Redis"
- Copie a `REDIS_URL` gerada
- Cole nas variáveis de ambiente da aplicação

#### Backup (Opcional)

- Configure backups automáticos
- Recomendado: diário às 3h AM

### 3. Domínio Customizado

1. **Adicionar domínio**
   - Settings → Domains
   - Add Domain: `seu-dominio.com`

2. **Configurar DNS**

   ```
   Type: A
   Name: @
   Value: [IP do EasyPanel]
   ```

3. **SSL/TLS**
   - EasyPanel configura automaticamente via Let's Encrypt
   - Aguarde 5-10 minutos

### 4. Volumes Persistentes

Os seguintes volumes são criados automaticamente:

```
/app/uploads  → Documentos enviados
/app/exports  → Relatórios exportados
/app/logs     → Logs da aplicação
```

## 🔍 Verificação

### Health Check

Após o deploy, verifique:

```bash
curl https://seu-dominio.com/health
```

Resposta esperada:

```json
{
  "status": "healthy"
}
```

### Endpoints

- Frontend: `https://seu-dominio.com`
- API: `https://seu-dominio.com/api/v1`
- Docs: `https://seu-dominio.com/docs`
- Health: `https://seu-dominio.com/health`

## 📊 Monitoramento

### Logs

Ver logs em tempo real:

- EasyPanel Dashboard → Logs
- Ou via CLI: `easypanel logs -f`

### Métricas

Monitorar no dashboard:

- CPU usage
- Memory usage
- Network traffic
- Request count

### Alertas

Configure alertas para:

- CPU > 80%
- Memory > 90%
- Health check failures
- Error rate > 5%

## 🔧 Troubleshooting

### Problema: Build falha

**Erro:** `failed to solve: process "/bin/sh -c npm run build" did not complete successfully`

**Solução:**

1. Verifique se `apps/frontend/package.json` existe
2. Verifique se há erros de TypeScript
3. Tente build local: `docker build -t test .`

### Problema: Backend não inicia

**Erro:** `OPENAI_API_KEY is not set`

**Solução:**

1. Verifique variáveis de ambiente no EasyPanel
2. Certifique-se que `OPENAI_API_KEY` está configurada
3. Redeploy a aplicação

### Problema: Database connection failed

**Erro:** `could not connect to server`

**Solução:**

1. Verifique se addon PostgreSQL está rodando
2. Verifique `DATABASE_URL` nas variáveis
3. Formato correto: `postgresql://user:pass@host:5432/db`

### Problema: Out of memory

**Erro:** `OOMKilled`

**Solução:**

1. Aumente memory limit em Resources
2. Recomendado mínimo: 1GB
3. Para produção: 2GB+

### Problema: Upload falha

**Erro:** `413 Request Entity Too Large`

**Solução:**

1. Verifique `MAX_UPLOAD_SIZE_MB` (padrão: 50MB)
2. Nginx já está configurado para 50MB
3. Aumente se necessário

## 🔄 Atualizações

### Deploy de Nova Versão

1. **Via GitHub (automático)**
   - Push para branch `main`
   - EasyPanel detecta e faz redeploy automático

2. **Via Docker Image**
   ```bash
   docker build -t gerador-relatorio-kiro:v1.1.0 .
   docker push your-registry/gerador-relatorio-kiro:v1.1.0
   ```

   - Atualize tag no EasyPanel
   - Redeploy

### Rollback

Se algo der errado:

1. EasyPanel → Deployments
2. Selecione versão anterior
3. Clique em "Rollback"

## 💰 Custos Estimados

### EasyPanel

- Hobby: $5/mês (1 servidor)
- Pro: $15/mês (3 servidores)
- Business: $50/mês (10 servidores)

### APIs

- OpenAI GPT-4o: ~$0.01-0.03 por relatório
- MiniMax M2.5: Gratuito
- **Com seleção inteligente: ~60% economia**

### Total Estimado (50 usuários)

- EasyPanel: $15/mês
- APIs: $50-150/mês (com otimização)
- **Total: $65-165/mês**

## 🎯 Otimizações

### Performance

1. **Enable caching**

   ```bash
   REDIS_URL=redis://redis:6379/0
   REDIS_CACHE_TTL=3600
   ```

2. **Increase workers**
   - Edite `infra/easypanel/supervisord.conf`
   - Aumente `--workers` baseado em CPU

3. **CDN para assets**
   - Configure CloudFlare na frente
   - Cache de assets estáticos

### Segurança

1. **Rate limiting**

   ```bash
   RATE_LIMIT_PER_MINUTE=60
   ```

2. **CORS**

   ```bash
   ALLOWED_ORIGINS=https://seu-dominio.com
   ```

3. **Firewall**
   - Configure no EasyPanel
   - Permita apenas portas 80/443

## 📚 Recursos

- [EasyPanel Docs](https://easypanel.io/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Configuration](https://nginx.org/en/docs/)

## 🆘 Suporte

### Logs Detalhados

```bash
# Backend logs
easypanel logs app --tail 100

# Nginx logs
easypanel exec app -- tail -f /var/log/nginx/error.log
```

### Shell Access

```bash
easypanel exec app -- /bin/bash
```

### Database Access

```bash
easypanel exec postgres -- psql -U user -d relatorio_db
```

## ✅ Checklist de Deploy

- [ ] Código no GitHub
- [ ] Variáveis de ambiente configuradas
- [ ] PostgreSQL addon adicionado
- [ ] Redis addon adicionado
- [ ] Domínio configurado (opcional)
- [ ] SSL ativo
- [ ] Health check passando
- [ ] Logs sem erros
- [ ] Teste de upload funcionando
- [ ] Teste de geração de relatório
- [ ] Backup configurado
- [ ] Monitoramento ativo

---

**Pronto!** Sua aplicação está rodando no EasyPanel! 🎉

Para suporte adicional, consulte a [documentação completa](../README.md) ou abra uma issue no GitHub.
