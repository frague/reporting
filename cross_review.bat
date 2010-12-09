rem Cross review table

rem cross_review.py --profile=ras



rem Progress charts update

rem charts.py --profile=ras


rem Rules catalogue

cd "D:\dev\BigRock\rep"
call git fetch dmaslennikov
call git reset dmaslennikov/ebcloud --hard
cd "D:\dev\reporting"
rules_catalog.py --profile=ras