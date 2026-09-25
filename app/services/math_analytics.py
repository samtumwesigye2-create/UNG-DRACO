from __future__ import annotations
from math import sqrt, log

def vector_norm(values:list[float])->float:
    return sqrt(sum(float(v)**2 for v in values))

def weighted_sum(values:list[float],weights:list[float])->float:
    if len(values)!=len(weights) or not values: raise ValueError("values and weights must be non-empty and equal length")
    total=sum(float(w) for w in weights)
    if total<=0: raise ValueError("weight total must be positive")
    return sum(float(v)*float(w) for v,w in zip(values,weights))/total

def delta(current:float,previous:float)->float:
    return float(current)-float(previous)

def derivative(current:float,previous:float,dt_seconds:float)->float:
    if dt_seconds<=0: raise ValueError("dt_seconds must be positive")
    return delta(current,previous)/float(dt_seconds)

def integral_trapezoid(samples:list[float],dt_seconds:float)->float:
    if dt_seconds<=0: raise ValueError("dt_seconds must be positive")
    if len(samples)<2: return 0.0
    return sum((float(a)+float(b))*0.5*dt_seconds for a,b in zip(samples,samples[1:]))

def gradient_1d(values:list[float],spacing:float=1.0)->list[float]:
    if spacing<=0: raise ValueError("spacing must be positive")
    if len(values)<2: return [0.0]*len(values)
    out=[]
    for i,v in enumerate(values):
        if i==0: g=(values[1]-v)/spacing
        elif i==len(values)-1: g=(v-values[i-1])/spacing
        else: g=(values[i+1]-values[i-1])/(2*spacing)
        out.append(float(g))
    return out

def threshold(value:float,operator:str,limit:float)->bool:
    ops={"<":lambda a,b:a<b,"<=":lambda a,b:a<=b,">":lambda a,b:a>b,">=":lambda a,b:a>=b,"==":lambda a,b:a==b,"!=":lambda a,b:a!=b}
    if operator not in ops: raise ValueError("unsupported threshold operator")
    return ops[operator](float(value),float(limit))

def approximately_equal(a:float,b:float,tolerance:float)->bool:
    if tolerance<0: raise ValueError("tolerance must be non-negative")
    return abs(float(a)-float(b))<=tolerance

def convergence(values:list[float],tolerance:float)->bool:
    if len(values)<2: return False
    return abs(float(values[-1])-float(values[-2]))<=tolerance

def sigma_residual(value:float,mean:float,stddev:float)->float:
    if stddev<=0: return 0.0 if value==mean else float("inf")
    return abs(float(value)-float(mean))/float(stddev)

def analytics_snapshot(current:list[float],previous:list[float]|None=None,dt_seconds:float|None=None)->dict:
    result={"norm":vector_norm(current)}
    if previous is not None and len(previous)==len(current):
        changes=[delta(a,b) for a,b in zip(current,previous)]
        result["delta"]=changes
        result["delta_norm"]=vector_norm(changes)
        if dt_seconds is not None and dt_seconds>0:
            result["rates"]=[derivative(a,b,dt_seconds) for a,b in zip(current,previous)]
    return result
