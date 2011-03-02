rem Cross review table

cross_review.py --profile=ras



rem Progress charts update

charts.py --profile=ras


rem Rules catalogue

cd "D:\dev\BigRock\rep"
call git fetch dmaslennikov
call git reset dmaslennikov/ebcloud --hard
cd "D:\dev\reporting"
rules_catalog.py --profile=ras


rem Daily statistics

kpis.py --profile=ras


rem jira to Rally sync

rally.py --profile=ras