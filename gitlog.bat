@echo off
cd d:\dev\BigRock\rep

rem git log --after="%1 00:00:00" --before="%2 00:00:00" --all --format=format:"%%ci|%%ce|%%s|%%ai|%%ad"

git log --after="%1 00:00:00" --all --format=format:"%%ci|%%ce|%%s|%%ai"
