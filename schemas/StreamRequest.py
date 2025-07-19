from pydantic import BaseModel, Field

class StreamRequest(BaseModel):
    text: str = Field(
        default=(
            "Please be informed that Mr. Md. Mahadi Hasan holds two accounts with Modhumoti Bank PLC "
            "(Account No. 112013800000010 and Account No. 114412200000042). On 06.11.2024, he executed two "
            "transactions via the GO SMART app—an NPSB transaction of 50,000 and a BEFTN transaction of 50,000. "
            "Both were marked as failed in the GO SMART admin panel logs, but amounts were debited according to the "
            "Bank Ultimas report. Investigate and explain the discrepancy."
        )
    )
