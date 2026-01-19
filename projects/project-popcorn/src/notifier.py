"""
알림 모듈

Microsoft Teams 웹훅을 통한 알림 발송

기능:
- 일일 스캔 결과 알림
- HIGH/CRITICAL 즉시 알림
- 에러 알림
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# 웹훅 URL (환경변수 또는 설정 파일)
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")


class TeamsNotifier:
    """Microsoft Teams 알림 클래스"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Args:
            webhook_url: Teams 웹훅 URL
        """
        self.webhook_url = webhook_url or TEAMS_WEBHOOK_URL

        if not self.webhook_url:
            print("[Notifier] 경고: TEAMS_WEBHOOK_URL 미설정")

    def send(self, message: dict) -> bool:
        """
        Teams로 메시지 발송

        Args:
            message: MessageCard 형식의 메시지

        Returns:
            성공 여부
        """
        if not self.webhook_url:
            print("[Notifier] 웹훅 URL 없음, 발송 건너뜀")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                print("[Notifier] 알림 발송 성공")
                return True
            else:
                print(f"[Notifier] 발송 실패: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"[Notifier] 발송 오류: {e}")
            return False

    def send_daily_summary(
        self,
        ministry: str,
        scan_date: str,
        total_bills: int,
        total_alerts: int,
        alerts_by_level: dict,
        top_alerts: list,
        report_path: Optional[str] = None,
    ) -> bool:
        """
        일일 요약 알림 발송

        Args:
            ministry: 부처명
            scan_date: 스캔 날짜
            total_bills: 스캔 법안 수
            total_alerts: 감지 법안 수
            alerts_by_level: Level별 건수
            top_alerts: 상위 알림 목록
            report_path: 리포트 경로

        Returns:
            성공 여부
        """
        # 색상 결정
        if alerts_by_level.get("CRITICAL", 0) > 0:
            theme_color = "FF0000"  # 빨강
            title_emoji = "🚨"
        elif alerts_by_level.get("HIGH", 0) > 0:
            theme_color = "FF5733"  # 주황
            title_emoji = "⚠️"
        elif total_alerts > 0:
            theme_color = "FFC300"  # 노랑
            title_emoji = "📢"
        else:
            theme_color = "28A745"  # 초록
            title_emoji = "✅"

        # 상위 알림 텍스트
        alerts_text = ""
        for i, alert in enumerate(top_alerts[:5], 1):
            level = alert.get("alert_level", "")
            name = alert.get("bill_name", "")[:40]
            score = alert.get("similarity_score", 0)
            if isinstance(score, (int, float)):
                alerts_text += f"{i}. [{level}] {name}... ({score:.2f})\n"
            else:
                alerts_text += f"{i}. [{level}] {name}...\n"

        if not alerts_text:
            alerts_text = "감지된 법안 없음"

        # MessageCard 구성
        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"Cross-Domain Radar {scan_date}",
            "sections": [
                {
                    "activityTitle": f"{title_emoji} Cross-Domain Radar 일일 알림",
                    "activitySubtitle": f"{ministry} | {scan_date}",
                    "facts": [
                        {"name": "스캔 법안", "value": f"{total_bills}건"},
                        {"name": "감지 법안", "value": f"{total_alerts}건"},
                        {"name": "CRITICAL", "value": f"{alerts_by_level.get('CRITICAL', 0)}건"},
                        {"name": "HIGH", "value": f"{alerts_by_level.get('HIGH', 0)}건"},
                        {"name": "MEDIUM", "value": f"{alerts_by_level.get('MEDIUM', 0)}건"},
                    ],
                    "markdown": True,
                },
                {
                    "title": "감지된 법안 (상위 5건)",
                    "text": f"```\n{alerts_text}```",
                },
            ],
        }

        # 리포트 링크 (선택)
        if report_path:
            message["potentialAction"] = [
                {
                    "@type": "OpenUri",
                    "name": "상세 리포트 보기",
                    "targets": [
                        {"os": "default", "uri": f"file://{report_path}"}
                    ],
                }
            ]

        return self.send(message)

    def send_alert(
        self,
        alert_level: str,
        bill_name: str,
        score: float,
        ministry: str,
        committee: str,
        proposer: str,
    ) -> bool:
        """
        단건 알림 발송 (HIGH/CRITICAL용)

        Args:
            alert_level: Alert Level
            bill_name: 법안명
            score: 유사도 스코어
            ministry: 타겟 부처
            committee: 소관 상임위
            proposer: 제안자

        Returns:
            성공 여부
        """
        color_map = {
            "CRITICAL": "FF0000",
            "HIGH": "FF5733",
            "MEDIUM": "FFC300",
            "LOW": "28A745",
        }

        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color_map.get(alert_level, "808080"),
            "summary": f"[{alert_level}] {bill_name[:30]}",
            "sections": [
                {
                    "activityTitle": f"🚨 [{alert_level}] Cross-Domain 법안 감지",
                    "activitySubtitle": f"{ministry}",
                    "facts": [
                        {"name": "법안명", "value": bill_name},
                        {"name": "유사도", "value": f"{score:.4f}"},
                        {"name": "소관위", "value": committee},
                        {"name": "제안자", "value": proposer},
                    ],
                    "markdown": True,
                }
            ],
        }

        return self.send(message)

    def send_error(self, error_message: str, context: str = "") -> bool:
        """
        에러 알림 발송

        Args:
            error_message: 에러 메시지
            context: 추가 컨텍스트

        Returns:
            성공 여부
        """
        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "DC3545",
            "summary": "Cross-Domain Radar 오류",
            "sections": [
                {
                    "activityTitle": "❌ Cross-Domain Radar 오류 발생",
                    "activitySubtitle": datetime.now().isoformat(),
                    "text": f"```\n{error_message}\n```",
                    "facts": [
                        {"name": "컨텍스트", "value": context or "N/A"},
                    ],
                    "markdown": True,
                }
            ],
        }

        return self.send(message)

    def send_test(self) -> bool:
        """테스트 알림 발송"""
        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": "Cross-Domain Radar 테스트",
            "sections": [
                {
                    "activityTitle": "🔔 Cross-Domain Radar 테스트 알림",
                    "activitySubtitle": datetime.now().isoformat(),
                    "text": "Teams 연동 테스트입니다.",
                    "markdown": True,
                }
            ],
        }

        return self.send(message)


def notify_scan_result(result: dict, webhook_url: Optional[str] = None) -> bool:
    """
    스캔 결과 알림 (편의 함수)

    Args:
        result: pipeline 스캔 결과
        webhook_url: Teams 웹훅 URL

    Returns:
        성공 여부
    """
    notifier = TeamsNotifier(webhook_url)

    # 알림 데이터 추출
    ministry = result.get("ministry", "")
    scan_date = result.get("scanned_at", "")[:10]
    total_bills = result.get("total_bills", 0)
    total_alerts = result.get("total_alerts", 0)
    alerts_by_level = result.get("alerts_by_level", {})

    # alerts 변환
    alerts = result.get("alerts", [])
    top_alerts = []
    for a in alerts[:5]:
        if hasattr(a, "to_dict"):
            top_alerts.append(a.to_dict())
        else:
            top_alerts.append(a)

    report_path = result.get("report_path")

    return notifier.send_daily_summary(
        ministry=ministry,
        scan_date=scan_date,
        total_bills=total_bills,
        total_alerts=total_alerts,
        alerts_by_level=alerts_by_level,
        top_alerts=top_alerts,
        report_path=report_path,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Teams 알림 테스트")
    parser.add_argument("--test", action="store_true", help="테스트 알림 발송")
    parser.add_argument("--url", type=str, help="Teams 웹훅 URL")

    args = parser.parse_args()

    notifier = TeamsNotifier(args.url)

    if args.test:
        success = notifier.send_test()
        print(f"테스트 결과: {'성공' if success else '실패'}")
    else:
        print("사용법: python -m src.notifier --test --url <WEBHOOK_URL>")
