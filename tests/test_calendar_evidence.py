import pytest
from nse_forecast.ingest.calendar_evidence import parse_circular,reconcile

TEXT='''Department: CAPITAL MARKET SEGMENT
Download Ref No: NSE/CMTR/54757 Date: December 08, 2022
Trading holidays for the calendar year 2023
Sr. No. Date Day Description
1 January 26, 2023 Thursday Republic Day
2 June 28, 2023 Wednesday Bakri Id
The holidays falling on Saturday / Sunday are as follows:
Sr. No. Date Day Description
1 November 12, 2023 Sunday Diwali-Laxmi Pujan*
*Muhurat Trading will be conducted on Sunday, November 12, 2023.
'''


def test_annual_notice_is_not_a_complete_calendar():
    evidence=parse_circular(TEXT)
    assert evidence['year']==2023 and evidence['complete_calendar'] is False
    assert evidence['published_date']=='2022-12-08'
    assert evidence['retrieved_at'] is None and evidence['published_at'] is None
    assert evidence['records'][-1]['claim']=='muhurat_session_announced'
    report=reconcile([evidence],{'NIFTY 50':['2023-06-28','2023-11-12']},'2023-06-28','2023-11-12')
    rows=report['comparisons']['NIFTY 50']
    assert rows['observed_on_annual_closure']==['2023-06-28']
    assert rows['announced_muhurat_present']==['2023-11-12']
    assert '2023-06-29' in rows['absent_from_candidate_weekdays']
    assert rows['weekend_observations_without_annual_session_notice']==[]
    assert report['calendar_verified'] is False and report['g0_passed'] is False


def test_wrapped_date_row_is_not_lost():
    text=TEXT.replace('1 January 26, 2023 Thursday Republic Day','1 January 26,2023\n Thursday Republic Day')
    assert parse_circular(text)['records'][0]['session_date']=='2023-01-26'


@pytest.mark.parametrize('text',[
    TEXT.replace('CAPITAL MARKET SEGMENT','CLEARING SEGMENT'),
    TEXT.replace('November 12, 2023 Sunday Diwali','November 13, 2023 Monday Diwali'),
    TEXT.replace('1 January 26, 2023 Thursday Republic Day','1 January 26, 2024 Friday Republic Day'),
    TEXT.replace('2 June 28, 2023 Wednesday Bakri Id','2 January 26, 2023 Thursday Duplicate'),
])
def test_wrong_segment_and_inconsistent_tables_fail_closed(text):
    with pytest.raises(ValueError):parse_circular(text)


def test_missing_years_and_unreconciled_annual_revisions_rejected():
    item=parse_circular(TEXT)
    with pytest.raises(ValueError,match='boundary-year'):
        reconcile([item],{},'2022-01-01','2023-12-31')
    with pytest.raises(ValueError,match='revision'):
        reconcile([item,item],{},'2023-01-01','2023-12-31')
