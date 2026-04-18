import uuid
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...deps import get_db
from ...models.user import User
from ...models.benchmark import BenchmarkRun
from ...schemas import benchmark as benchmark_schema
from .auth import get_current_user

router = APIRouter()

@router.post("/results", response_model=benchmark_schema.BenchmarkRun, status_code=status.HTTP_201_CREATED)
async def submit_benchmark_results(
    data: benchmark_schema.BenchmarkRunBase,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    run_id = str(uuid.uuid4())
    run = BenchmarkRun(
        id=run_id,
        user_id=current_user.id,
        model=data.model,
        overall_score=data.overall_score,
        results=data.results
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run

@router.get("/{run_id}", response_model=benchmark_schema.BenchmarkRun)
async def get_benchmark(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return run

@router.get("/{run_id}/report", response_class=HTMLResponse)
async def get_benchmark_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    
    # Generate the HTML Report
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Inter', system-ui, sans-serif; background: #0a0a0f; color: #fff; padding: 2rem; }}
  .container {{ max-width: 800px; margin: 0 auto; background: #1a1a24; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); border: 1px solid #333; }}
  h1 {{ color: #00e5cc; }}
  .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #333; padding-bottom: 1rem; margin-bottom: 2rem; }}
  .row {{ display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid #222; }}
  .bar-bg {{ background: #333; width: 200px; height: 12px; border-radius: 6px; overflow: hidden; }}
  .bar-fill {{ background: #00e5cc; height: 100%; }}
  .score {{ font-weight: bold; width: 80px; text-align: right; }}
  .overall {{ font-size: 1.5rem; margin-top: 2rem; padding-top: 1rem; border-top: 2px solid #333; text-align: center; color: #ffb347; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>NeuroSleepNet Benchmark</h1>
        <div>Model: <strong>{run.model}</strong></div>
      </div>
      <div style="text-align: right; color: #888;">
        <div>Date: {run.created_at.strftime('%Y-%m-%d')}</div>
        <div>ID: {run.id}</div>
      </div>
    </div>
"""
    for res in run.results:
        score = res.get("score", 0.0)
        name = res.get("scenario", "Unknown")
        html += f"""
    <div class="row">
      <div style="width: 250px;">{name}</div>
      <div class="bar-bg"><div class="bar-fill" style="width: {score}%;"></div></div>
      <div class="score">{score:.0f}% ✓</div>
    </div>
"""
    
    html += f"""
    <div class="overall">
      Overall Memory Score: {int(run.overall_score)}/100 🧠
    </div>
  </div>
</body>
</html>"""
    
    return HTMLResponse(content=html)

@router.get("/{run_id}/badge", response_class=Response)
async def get_benchmark_badge(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BenchmarkRun).where(BenchmarkRun.id == run_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
        
    score = int(run.overall_score)
    color = "#4c1" if score > 80 else "#a4a61d" if score > 50 else "#e05d44"
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="160" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h105v20H0z"/>
    <path fill="{color}" d="M105 0h55v20H105z"/>
    <path fill="url(#b)" d="M0 0h160v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="52.5" y="15" fill="#010101" fill-opacity=".3">Memory Score</text>
    <text x="52.5" y="14">Memory Score</text>
    <text x="131.5" y="15" fill="#010101" fill-opacity=".3">{score}/100</text>
    <text x="131.5" y="14">{score}/100</text>
  </g>
</svg>"""
    return Response(content=svg, media_type="image/svg+xml")
