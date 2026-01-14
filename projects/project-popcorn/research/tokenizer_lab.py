"""
국회법 용어 토크나이징 비교 실험

tiktoken vs tokenizers 성능 비교
- 토큰 수 비교
- 한국어 법률 용어 처리 품질
"""
import tiktoken
from tokenizers import Tokenizer

# 테스트 문장 (국회법 관련)
TEST_SENTENCES = [
    "국회의원은 국회에서 직무상 행한 발언과 표결에 관하여 국회 외에서 책임을 지지 아니한다.",
    "위원회는 그 소관에 속하는 의안과 청원 등의 심사, 그 밖에 법률에서 정하는 직무를 행한다.",
    "본회의는 재적의원 5분의 1 이상의 출석으로 개의하고, 재적의원 과반수의 출석과 출석의원 과반수의 찬성으로 의결한다.",
]


def compare_tokenizers():
    """토크나이저 비교 분석"""
    # TODO: tiktoken 토큰화
    # TODO: tokenizers (Upstage) 토큰화
    # TODO: 결과 비교 분석
    pass


if __name__ == "__main__":
    compare_tokenizers()
