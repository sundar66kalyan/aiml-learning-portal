@echo off
echo ========================================
echo AI/ML Learning Portal - Deployment Script
echo Created by Kalyanasundar
echo ========================================
echo.

echo Step 1: Checking git status...
git status

echo.
echo Step 2: Adding changes...
git add .

echo.
echo Step 3: Committing changes...
set /p commit_msg="Enter commit message: "
git commit -m "%commit_msg%"

echo.
echo Step 4: Pushing to GitHub...
git push origin main

echo.
echo Step 5: Deployment initiated!
echo Your changes will be automatically deployed to:
echo - Render: https://aiml-learning-portal.onrender.com
echo.
echo Deployment complete!
pause
