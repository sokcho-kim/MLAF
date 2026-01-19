"""
이메일 알림 모듈

SMTP를 통한 이메일 알림 발송

기능:
- 일일 스캔 결과 이메일 (HTML 형식)
- HIGH/CRITICAL 즉시 알림
- 리포트 첨부 (선택)
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

# 이메일 설정 (환경변수)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Gmail: 앱 비밀번호
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")  # 쉼표로 구분


class EmailNotifier:
    """이메일 알림 클래스"""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        email_from: str = None,
        email_to: str = None,
    ):
        self.smtp_host = smtp_host or SMTP_HOST
        self.smtp_port = smtp_port or SMTP_PORT
        self.smtp_user = smtp_user or SMTP_USER
        self.smtp_password = smtp_password or SMTP_PASSWORD
        self.email_from = email_from or EMAIL_FROM
        self.email_to = email_to or EMAIL_TO

        if not all([self.smtp_user, self.smtp_password, self.email_from, self.email_to]):
            print("[EmailNotifier] 경고: 이메일 설정 미완료")

    def _get_recipients(self) -> List[str]:
        """수신자 목록 반환"""
        if isinstance(self.email_to, str):
            return [e.strip() for e in self.email_to.split(",") if e.strip()]
        return self.email_to

    def send(
        self,
        subject: str,
        body_html: str,
        body_text: str = None,
        attachments: List[str] = None,
    ) -> bool:
        """
        이메일 발송

        Args:
            subject: 제목
            body_html: HTML 본문
            body_text: 텍스트 본문 (선택)
            attachments: 첨부파일 경로 목록

        Returns:
            성공 여부
        """
        if not all([self.smtp_user, self.smtp_password, self.email_from, self.email_to]):
            print("[EmailNotifier] 이메일 설정 없음, 발송 건너뜀")
            return False

        try:
            # 메시지 구성
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from
            msg["To"] = self.email_to

            # 텍스트/HTML 본문
            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            # 첨부파일
            if attachments:
                for filepath in attachments:
                    if Path(filepath).exists():
                        with open(filepath, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = Path(filepath).name
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={filename}",
                        )
                        msg.attach(part)

            # SMTP 발송
            recipients = self._get_recipients()
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, recipients, msg.as_string())

            print(f"[EmailNotifier] 이메일 발송 성공: {len(recipients)}명")
            return True

        except Exception as e:
            print(f"[EmailNotifier] 발송 오류: {e}")
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
        일일 요약 이메일 발송

        Args:
            ministry: 부처명
            scan_date: 스캔 날짜
            total_bills: 스캔 법안 수
            total_alerts: 감지 법안 수
            alerts_by_level: Level별 건수
            top_alerts: 상위 알림 목록
            report_path: 리포트 파일 경로

        Returns:
            성공 여부
        """
        # 제목 결정
        critical = alerts_by_level.get("CRITICAL", 0)
        high = alerts_by_level.get("HIGH", 0)

        if critical > 0:
            emoji = "🚨"
            priority = "[긴급]"
        elif high > 0:
            emoji = "⚠️"
            priority = "[주의]"
        elif total_alerts > 0:
            emoji = "📢"
            priority = ""
        else:
            emoji = "✅"
            priority = ""

        subject = f"{emoji} {priority} Cross-Domain Radar 일일 리포트 ({scan_date}) - {ministry}"

        # HTML 본문
        alerts_rows = ""
        for i, alert in enumerate(top_alerts[:10], 1):
            level = alert.get("alert_level", "")
            name = alert.get("bill_name", "")[:50]
            score = alert.get("similarity_score", 0)
            committee = alert.get("committee", "")[:20]

            level_color = {
                "CRITICAL": "#dc3545",
                "HIGH": "#fd7e14",
                "MEDIUM": "#ffc107",
                "LOW": "#28a745",
            }.get(level, "#6c757d")

            if isinstance(score, (int, float)):
                score_str = f"{score:.3f}"
            else:
                score_str = str(score)

            alerts_rows += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{i}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">
                    <span style="background-color: {level_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{level}</span>
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{name}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: center;">{score_str}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{committee}</td>
            </tr>
            """

        if not alerts_rows:
            alerts_rows = """
            <tr>
                <td colspan="5" style="padding: 20px; text-align: center; color: #6c757d;">
                    감지된 법안이 없습니다.
                </td>
            </tr>
            """

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Malgun Gothic', '맑은 고딕', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #fff; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 8px 8px; }}
                .summary-box {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .summary-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; min-width: 100px; }}
                .summary-number {{ font-size: 28px; font-weight: bold; color: #495057; }}
                .summary-label {{ font-size: 12px; color: #6c757d; }}
                .critical {{ color: #dc3545; }}
                .high {{ color: #fd7e14; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #f8f9fa; padding: 12px 8px; text-align: left; border-bottom: 2px solid #dee2e6; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">{emoji} Cross-Domain Radar</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">{ministry} | {scan_date}</p>
                </div>
                <div class="content">
                    <div class="summary-box">
                        <div class="summary-item">
                            <div class="summary-number">{total_bills}</div>
                            <div class="summary-label">스캔 법안</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-number">{total_alerts}</div>
                            <div class="summary-label">감지 법안</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-number critical">{critical}</div>
                            <div class="summary-label">CRITICAL</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-number high">{high}</div>
                            <div class="summary-label">HIGH</div>
                        </div>
                    </div>

                    <h3>📋 감지된 법안 (상위 10건)</h3>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 40px;">#</th>
                                <th style="width: 80px;">Level</th>
                                <th>법안명</th>
                                <th style="width: 70px; text-align: center;">스코어</th>
                                <th style="width: 120px;">소관위</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts_rows}
                        </tbody>
                    </table>

                    <div class="footer">
                        <p>본 메일은 Cross-Domain Radar 시스템에서 자동 발송되었습니다.</p>
                        <p>문의: Cross-Domain Radar Team</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        # 텍스트 버전
        body_text = f"""
Cross-Domain Radar 일일 리포트
==============================
부처: {ministry}
날짜: {scan_date}

요약
----
- 스캔 법안: {total_bills}건
- 감지 법안: {total_alerts}건
- CRITICAL: {critical}건
- HIGH: {high}건

상위 감지 법안
--------------
"""
        for i, alert in enumerate(top_alerts[:10], 1):
            name = alert.get("bill_name", "")[:40]
            level = alert.get("alert_level", "")
            body_text += f"{i}. [{level}] {name}\n"

        # 첨부파일
        attachments = []
        if report_path and Path(report_path).exists():
            attachments.append(report_path)

        return self.send(subject, body_html, body_text, attachments)

    def send_alert(
        self,
        alert_level: str,
        bill_name: str,
        score: float,
        ministry: str,
        committee: str,
        proposer: str,
        bill_id: str = "",
    ) -> bool:
        """
        단건 알림 발송 (HIGH/CRITICAL용)
        """
        level_info = {
            "CRITICAL": ("🚨", "#dc3545", "[긴급]"),
            "HIGH": ("⚠️", "#fd7e14", "[주의]"),
        }.get(alert_level, ("📢", "#6c757d", ""))

        emoji, color, priority = level_info
        subject = f"{emoji} {priority} [{alert_level}] Cross-Domain 법안 감지: {bill_name[:30]}"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Malgun Gothic', sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 2px solid {color}; border-radius: 8px; overflow: hidden;">
                <div style="background: {color}; color: white; padding: 15px;">
                    <h2 style="margin: 0;">{emoji} [{alert_level}] Cross-Domain 법안 감지</h2>
                </div>
                <div style="padding: 20px;">
                    <table style="width: 100%;">
                        <tr><td style="padding: 8px 0; color: #6c757d;">법안명</td><td style="padding: 8px 0; font-weight: bold;">{bill_name}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6c757d;">유사도 스코어</td><td style="padding: 8px 0;">{score:.4f}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6c757d;">타겟 부처</td><td style="padding: 8px 0;">{ministry}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6c757d;">소관위원회</td><td style="padding: 8px 0;">{committee}</td></tr>
                        <tr><td style="padding: 8px 0; color: #6c757d;">제안자</td><td style="padding: 8px 0;">{proposer}</td></tr>
                    </table>
                    <p style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px; font-size: 14px;">
                        ⚡ 본 법안은 {ministry} 소관 업무와 높은 연관성이 감지되었습니다. 검토가 필요합니다.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return self.send(subject, body_html)

    def send_test(self) -> bool:
        """테스트 이메일 발송"""
        subject = "🔔 Cross-Domain Radar 테스트 이메일"
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Malgun Gothic', sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; text-align: center; padding: 40px; border: 1px solid #dee2e6; border-radius: 8px;">
                <h2>🔔 Cross-Domain Radar</h2>
                <p>이메일 알림 테스트입니다.</p>
                <p style="color: #6c757d; font-size: 14px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        return self.send(subject, body_html)


def notify_scan_result_email(result: dict) -> bool:
    """
    스캔 결과 이메일 알림 (편의 함수)

    Args:
        result: pipeline 스캔 결과

    Returns:
        성공 여부
    """
    notifier = EmailNotifier()

    ministry = result.get("ministry", "")
    scan_date = result.get("scanned_at", "")[:10]
    total_bills = result.get("total_bills", 0)
    total_alerts = result.get("total_alerts", 0)
    alerts_by_level = result.get("alerts_by_level", {})

    alerts = result.get("alerts", [])
    top_alerts = []
    for a in alerts[:10]:
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

    parser = argparse.ArgumentParser(description="이메일 알림 테스트")
    parser.add_argument("--test", action="store_true", help="테스트 이메일 발송")

    args = parser.parse_args()

    notifier = EmailNotifier()

    if args.test:
        success = notifier.send_test()
        print(f"테스트 결과: {'성공' if success else '실패'}")
    else:
        print("사용법: python -m src.notifier_email --test")
