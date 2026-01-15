"""
임베딩 모델 비교 테스트

3개 모델로 Cross-Domain 감지율 측정:
1. Solar Embedding (Upstage API)
2. text-embedding-3-small (OpenAI API)
3. Multilingual-E5-Large (fastembed 로컬)
"""
import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import time

load_dotenv()

# API Keys
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

DATA_DIR = Path(__file__).parent.parent / "data"


def load_data() -> Tuple[dict, List[dict], List[dict]]:
    """데이터 로드"""
    # 산업통상부 R&R (증강 버전)
    rr_data = json.load(open(DATA_DIR / "ministry_rr_augmented.json", 'r', encoding='utf-8'))
    industry_rr = None
    for m in rr_data['ministries']:
        if m['ministry_name'] == '산업통상부':
            industry_rr = m
            break

    # 법안 100건
    bills_data = json.load(open(DATA_DIR / "test_bills.json", 'r', encoding='utf-8'))
    bills = bills_data['bills']

    # Golden Set
    golden_data = json.load(open(DATA_DIR / "golden_set.json", 'r', encoding='utf-8'))
    golden_set = golden_data['bills']

    return industry_rr, bills, golden_set


# ============================================================
# 1. Solar Embedding (Upstage API)
# ============================================================
def embed_solar(texts: List[str]) -> List[List[float]]:
    """Solar Embedding API 호출"""
    import httpx

    url = "https://api.upstage.ai/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {UPSTAGE_API_KEY}",
        "Content-Type": "application/json"
    }

    embeddings = []
    for i, text in enumerate(texts):
        # 텍스트 길이 제한 (4096 토큰 ≈ 8000자)
        truncated = text[:8000]

        data = {
            "model": "embedding-passage",
            "input": truncated
        }

        try:
            response = httpx.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            emb = result['data'][0]['embedding']
            embeddings.append(emb)

            if (i + 1) % 10 == 0:
                print(f"    Solar: {i+1}/{len(texts)}")

        except Exception as e:
            print(f"    [ERROR] Solar embedding failed: {e}")
            embeddings.append([0.0] * 4096)

        time.sleep(0.1)  # Rate limit

    return embeddings


# ============================================================
# 2. OpenAI text-embedding-3-small
# ============================================================
def embed_openai(texts: List[str]) -> List[List[float]]:
    """OpenAI Embedding API 호출"""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

    embeddings = []
    for i, text in enumerate(texts):
        truncated = text[:8000]

        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=truncated
            )
            emb = response.data[0].embedding
            embeddings.append(emb)

            if (i + 1) % 10 == 0:
                print(f"    OpenAI: {i+1}/{len(texts)}")

        except Exception as e:
            print(f"    [ERROR] OpenAI embedding failed: {e}")
            embeddings.append([0.0] * 1536)

        time.sleep(0.05)

    return embeddings


# ============================================================
# 3. Multilingual E5 Large (fastembed)
# ============================================================
def embed_multilingual_e5(texts: List[str]) -> List[List[float]]:
    """Multilingual E5 Large 로컬 임베딩"""
    try:
        from fastembed import TextEmbedding
    except ImportError:
        print("    [ERROR] fastembed not installed")
        return [[0.0] * 1024 for _ in texts]

    model = TextEmbedding("intfloat/multilingual-e5-large")
    embeddings = list(model.embed(texts))

    print(f"    Multilingual-E5: {len(embeddings)}/{len(texts)}")
    return [emb.tolist() for emb in embeddings]


# ============================================================
# 유사도 계산 및 랭킹
# ============================================================
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """코사인 유사도"""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def rank_bills(rr_embedding: List[float], bill_embeddings: List[List[float]], bills: List[dict]) -> List[dict]:
    """유사도 기준 법안 랭킹"""
    scores = []
    for i, bill_emb in enumerate(bill_embeddings):
        sim = cosine_similarity(rr_embedding, bill_emb)
        scores.append({
            'rank': 0,
            'bill_name': bills[i]['bill_name'],
            'bill_id': bills[i].get('bill_id'),
            'committee': bills[i].get('committee', ''),
            'similarity': sim
        })

    # 유사도 내림차순 정렬
    scores.sort(key=lambda x: x['similarity'], reverse=True)

    # 순위 부여
    for i, item in enumerate(scores):
        item['rank'] = i + 1

    return scores


def evaluate_golden_set(rankings: List[dict], golden_set: List[dict]) -> dict:
    """Golden Set 평가"""
    golden_ids = {g['bill_id'] for g in golden_set}

    # Golden Set 법안들의 순위 찾기
    golden_ranks = []
    for g in golden_set:
        for r in rankings:
            if r['bill_id'] == g['bill_id']:
                golden_ranks.append({
                    'golden_id': g['golden_id'],
                    'difficulty': g['difficulty'],
                    'bill_name': g['bill_name'][:30],
                    'rank': r['rank'],
                    'similarity': r['similarity']
                })
                break

    # Recall@K 계산
    recall_at_10 = len([g for g in golden_ranks if g['rank'] <= 10]) / len(golden_set)
    recall_at_20 = len([g for g in golden_ranks if g['rank'] <= 20]) / len(golden_set)
    recall_at_50 = len([g for g in golden_ranks if g['rank'] <= 50]) / len(golden_set)

    # Hard 난이도 평균 순위
    hard_ranks = [g['rank'] for g in golden_ranks if g['difficulty'] == 'Hard']
    avg_hard_rank = np.mean(hard_ranks) if hard_ranks else 999

    return {
        'golden_ranks': golden_ranks,
        'recall_at_10': recall_at_10,
        'recall_at_20': recall_at_20,
        'recall_at_50': recall_at_50,
        'avg_hard_rank': avg_hard_rank,
        'mean_rank': np.mean([g['rank'] for g in golden_ranks])
    }


# ============================================================
# 메인 테스트
# ============================================================
def run_embedding_test():
    """임베딩 비교 테스트 실행"""
    print("=" * 70)
    print("임베딩 모델 비교 테스트: Cross-Domain 감지율")
    print("=" * 70)

    # 데이터 로드
    print("\n[1/5] 데이터 로드...")
    industry_rr, bills, golden_set = load_data()

    print(f"  - 산업통상부 R&R: {len(industry_rr['augmented_text'])}자")
    print(f"  - 법안: {len(bills)}건")
    print(f"  - Golden Set: {len(golden_set)}건")

    # Golden Set 법안을 bills에 추가 (없는 경우)
    bill_ids = {b.get('bill_id') for b in bills}
    for g in golden_set:
        if g['bill_id'] not in bill_ids:
            bills.append({
                'bill_id': g['bill_id'],
                'bill_name': g['bill_name'],
                'committee': g['committee'],
            })
    print(f"  - 테스트 법안 (Golden 포함): {len(bills)}건")

    # 텍스트 준비
    rr_text = industry_rr['augmented_text']
    bill_texts = [b['bill_name'] for b in bills]  # 의안명만 사용 (제안이유는 API로 별도 수집 필요)

    results = {}

    # ============================================================
    # Model 1: Solar Embedding
    # ============================================================
    print("\n[2/5] Solar Embedding 테스트...")
    try:
        solar_rr_emb = embed_solar([rr_text])[0]
        solar_bill_embs = embed_solar(bill_texts)

        solar_rankings = rank_bills(solar_rr_emb, solar_bill_embs, bills)
        solar_eval = evaluate_golden_set(solar_rankings, golden_set)

        results['solar'] = {
            'model': 'Solar Embedding (Upstage)',
            'evaluation': solar_eval,
            'top_10': solar_rankings[:10]
        }
        print(f"  Recall@10: {solar_eval['recall_at_10']:.1%}")
        print(f"  Hard 평균 순위: {solar_eval['avg_hard_rank']:.1f}")
    except Exception as e:
        print(f"  [ERROR] Solar 테스트 실패: {e}")
        results['solar'] = {'error': str(e)}

    # ============================================================
    # Model 2: OpenAI text-embedding-3-small
    # ============================================================
    print("\n[3/5] OpenAI Embedding 테스트...")
    try:
        openai_rr_emb = embed_openai([rr_text])[0]
        openai_bill_embs = embed_openai(bill_texts)

        openai_rankings = rank_bills(openai_rr_emb, openai_bill_embs, bills)
        openai_eval = evaluate_golden_set(openai_rankings, golden_set)

        results['openai'] = {
            'model': 'text-embedding-3-small (OpenAI)',
            'evaluation': openai_eval,
            'top_10': openai_rankings[:10]
        }
        print(f"  Recall@10: {openai_eval['recall_at_10']:.1%}")
        print(f"  Hard 평균 순위: {openai_eval['avg_hard_rank']:.1f}")
    except Exception as e:
        print(f"  [ERROR] OpenAI 테스트 실패: {e}")
        results['openai'] = {'error': str(e)}

    # ============================================================
    # Model 3: Multilingual E5 Large
    # ============================================================
    print("\n[4/5] Multilingual-E5 테스트...")
    try:
        e5_rr_emb = embed_multilingual_e5([rr_text])[0]
        e5_bill_embs = embed_multilingual_e5(bill_texts)

        e5_rankings = rank_bills(e5_rr_emb, e5_bill_embs, bills)
        e5_eval = evaluate_golden_set(e5_rankings, golden_set)

        results['multilingual_e5'] = {
            'model': 'Multilingual-E5-Large (fastembed)',
            'evaluation': e5_eval,
            'top_10': e5_rankings[:10]
        }
        print(f"  Recall@10: {e5_eval['recall_at_10']:.1%}")
        print(f"  Hard 평균 순위: {e5_eval['avg_hard_rank']:.1f}")
    except Exception as e:
        print(f"  [ERROR] Multilingual-E5 테스트 실패: {e}")
        results['multilingual_e5'] = {'error': str(e)}

    # ============================================================
    # 결과 저장 및 출력
    # ============================================================
    print("\n[5/5] 결과 저장...")
    output_path = Path(__file__).parent / "results" / "embedding_comparison.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"  저장: {output_path}")

    # 최종 결과 출력
    print("\n" + "=" * 70)
    print("Cross-Domain 감지율 비교 결과")
    print("=" * 70)
    print(f"{'모델':<35} {'Recall@10':<12} {'Recall@20':<12} {'Hard 순위':<12}")
    print("-" * 70)

    for model_key in ['solar', 'openai', 'multilingual_e5']:
        if model_key in results and 'evaluation' in results[model_key]:
            eval_data = results[model_key]['evaluation']
            model_name = results[model_key]['model'][:33]
            r10 = f"{eval_data['recall_at_10']:.1%}"
            r20 = f"{eval_data['recall_at_20']:.1%}"
            hard = f"{eval_data['avg_hard_rank']:.1f}"
            print(f"{model_name:<35} {r10:<12} {r20:<12} {hard:<12}")

    # Golden Set 상세 순위
    print("\n" + "=" * 70)
    print("Golden Set 상세 순위")
    print("=" * 70)

    for model_key in ['solar', 'openai', 'multilingual_e5']:
        if model_key in results and 'evaluation' in results[model_key]:
            print(f"\n[{results[model_key]['model']}]")
            for g in results[model_key]['evaluation']['golden_ranks']:
                diff = g['difficulty']
                rank = g['rank']
                name = g['bill_name'][:25]
                sim = g['similarity']
                marker = "★" if rank <= 10 else ""
                print(f"  {diff:<8} #{rank:<3} {name:<27} (sim: {sim:.3f}) {marker}")

    return results


if __name__ == "__main__":
    run_embedding_test()
