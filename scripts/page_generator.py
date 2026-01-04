#!/usr/bin/env python3
"""
AI Digest - Gerador de Páginas para o Site Astro
Gera arquivos markdown com análises profundas traduzidas para português
"""
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import unicodedata

# Configurações
SITE_CONTENT_DIR = Path(__file__).parent.parent / "src" / "content" / "articles"
CLAUDE_PATH = os.environ.get("CLAUDE_PATH", "/home/joyboy/.claude/local/claude")


def slugify(text: str) -> str:
    """Converte texto para slug URL-safe."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text[:60]


def estimate_reading_time(text: str) -> str:
    """Estima tempo de leitura baseado em 200 palavras/min."""
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min"


def generate_article_content(item: Dict, item_type: str) -> str:
    """Usa Claude para gerar artigo completo em português."""

    type_prompts = {
        "news": f"""Você é um jornalista de tecnologia escrevendo para o AI Digest.

NOTÍCIA ORIGINAL:
Título: {item.get('title', '')}
URL: {item.get('url', '')}
Resumo: {item.get('summary', '')}
Fonte: {item.get('source_name', '')}

Escreva um artigo COMPLETO em português brasileiro com:
1. Explicação detalhada do que aconteceu
2. Por que isso importa para profissionais de tecnologia
3. Contexto histórico se relevante
4. Impacto prático
5. O que esperar a seguir

Use markdown com headers ##. Seja informativo mas acessível.
Mínimo 400 palavras. Máximo 800 palavras.""",

        "paper": f"""Você é um pesquisador de IA escrevendo para o AI Digest.

PAPER ACADÊMICO:
Título: {item.get('title', '')}
URL: {item.get('url', '')}
Abstract: {item.get('summary', item.get('abstract', ''))}
Categoria: {item.get('category', '')}

Escreva uma EXPLICAÇÃO COMPLETA em português brasileiro com:
1. O que o paper propõe (em linguagem acessível)
2. Metodologia utilizada (simplificada)
3. Principais resultados e descobertas
4. Limitações do estudo
5. Aplicações práticas potenciais
6. Por que isso importa para a indústria

Use markdown com headers ##. Traduza termos técnicos quando possível.
Mínimo 500 palavras. Máximo 1000 palavras.""",

        "repo": f"""Você é um desenvolvedor sênior escrevendo para o AI Digest.

REPOSITÓRIO GITHUB:
Nome: {item.get('name', '')}
URL: {item.get('url', '')}
Descrição: {item.get('description', '')}
Stars: {item.get('stars', 'N/A')}
Linguagem: {item.get('language', 'N/A')}

Escreva um GUIA COMPLETO em português brasileiro com:
1. O que é e para que serve
2. Como instalar e configurar (com código)
3. Exemplo prático de uso
4. Prós e contras
5. Quando usar (e quando não usar)
6. Alternativas populares

Use markdown com headers ## e blocos de código ```.
Mínimo 400 palavras. Máximo 700 palavras."""
    }

    prompt = type_prompts.get(item_type, type_prompts["news"])

    try:
        result = subprocess.run(
            [CLAUDE_PATH, "-p", prompt, "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=300
        )
        content = result.stdout.strip()

        # Limpa possíveis marcadores de código
        if content.startswith("```markdown"):
            content = content[11:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    except Exception as e:
        print(f"Erro ao gerar conteúdo: {e}")
        return generate_fallback_content(item, item_type)


def generate_fallback_content(item: Dict, item_type: str) -> str:
    """Conteúdo fallback se Claude falhar."""
    title = item.get('title', item.get('name', 'Sem título'))
    summary = item.get('summary', item.get('description', ''))
    url = item.get('url', '')

    return f"""## Sobre

{summary}

## Fonte Original

Este conteúdo foi curado automaticamente pelo AI Digest. Para mais detalhes, consulte a [fonte original]({url}).

---

*Artigo gerado automaticamente. Uma análise mais profunda será adicionada em breve.*
"""


def create_article_file(item: Dict, item_type: str, date: datetime) -> Path:
    """Cria arquivo markdown para um item."""

    title = item.get('title', item.get('name', 'Sem título'))
    slug = slugify(title)
    date_str = date.strftime("%Y-%m-%d")
    filename = f"{date_str}-{slug}.md"
    filepath = SITE_CONTENT_DIR / filename

    # Pula se já existe
    if filepath.exists():
        print(f"  ⏭️  Já existe: {filename}")
        return filepath

    print(f"  📝 Gerando: {title[:50]}...")

    # Gera conteúdo com Claude
    content = generate_article_content(item, item_type)

    # Monta frontmatter
    category_map = {"news": "news", "paper": "paper", "repo": "repo"}
    category = category_map.get(item_type, "news")

    description = item.get('summary', item.get('description', ''))[:200]
    if len(description) == 200:
        description = description[:197] + "..."

    tags = []
    if item.get('matched_keywords'):
        tags = item['matched_keywords'][:5]
    elif item.get('language'):
        tags = [item['language']]

    reading_time = estimate_reading_time(content)

    frontmatter = f'''---
title: "{title.replace('"', "'")}"
description: "{description.replace('"', "'")}"
pubDate: {date_str}
category: {category}
originalUrl: "{item.get('url', '')}"
author: "AI Digest"
readingTime: "{reading_time}"
tags: {json.dumps(tags, ensure_ascii=False)}
---

'''

    # Salva arquivo
    SITE_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)

    print(f"  ✅ Criado: {filename}")
    return filepath


def generate_pages_from_data(data: Dict) -> List[Path]:
    """Gera páginas para todos os itens curados."""

    created_files = []
    date = datetime.now()

    print("\n📄 Gerando páginas para o site...\n")

    # Papers
    papers = data.get('papers', [])[:3]  # Top 3 papers
    if papers:
        print("📄 Papers:")
        for paper in papers:
            try:
                filepath = create_article_file(paper, 'paper', date)
                created_files.append(filepath)
            except Exception as e:
                print(f"  ❌ Erro: {e}")

    # Repos
    repos = data.get('repos', [])[:3]  # Top 3 repos
    if repos:
        print("\n⭐ Repositórios:")
        for repo in repos:
            try:
                filepath = create_article_file(repo, 'repo', date)
                created_files.append(filepath)
            except Exception as e:
                print(f"  ❌ Erro: {e}")

    # News
    news = data.get('news', [])[:5]  # Top 5 notícias
    if news:
        print("\n📰 Notícias:")
        for item in news:
            try:
                filepath = create_article_file(item, 'news', date)
                created_files.append(filepath)
            except Exception as e:
                print(f"  ❌ Erro: {e}")

    print(f"\n✅ Total de páginas criadas: {len(created_files)}")
    return created_files


def trigger_site_rebuild():
    """Faz commit e push para triggerar rebuild no Vercel."""
    try:
        site_dir = SITE_CONTENT_DIR.parent.parent.parent

        subprocess.run(
            ["git", "add", "-A"],
            cwd=site_dir, capture_output=True
        )

        result = subprocess.run(
            ["git", "commit", "-m", f"📝 Novos artigos - {datetime.now().strftime('%d/%m/%Y')}"],
            cwd=site_dir, capture_output=True, text=True
        )

        if "nothing to commit" in result.stdout + result.stderr:
            print("📦 Nenhuma mudança para commit")
            return False

        subprocess.run(
            ["git", "push"],
            cwd=site_dir, capture_output=True
        )

        print("🚀 Push realizado - Vercel vai rebuildar automaticamente")
        return True

    except Exception as e:
        print(f"⚠️ Erro no git: {e}")
        return False


if __name__ == "__main__":
    import sys

    # Pode receber path para JSON como argumento
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
            generate_pages_from_data(data)
            trigger_site_rebuild()
        else:
            print(f"Arquivo não encontrado: {json_path}")
    else:
        print("Uso: python page_generator.py <caminho_para_collected_data.json>")
