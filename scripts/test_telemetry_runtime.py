#!/usr/bin/env python3
"""Explicit live API smoke test. Synthetic text, no microphone/audio recording.
Run using agent-starter-python's uv environment. --live confirms provider usage.
"""
import argparse
import asyncio
import json
import logging
from pathlib import Path

import httpx
from livekit import rtc

ROOT=Path(__file__).resolve().parents[1]

async def run(base,scenario):
    result={'scenario':scenario,'microphone':False,'synthetic_input':True,'audio_samples':0,'nonzero_frames':0,'agent_states':[],'avatars':[]}
    room=rtc.Room();tasks=set();completed=asyncio.Event();speaking=False
    async def consume(track):
        stream=rtc.AudioStream(track)
        try:
            async for ev in stream:
                result['audio_samples']+=ev.frame.samples_per_channel
                if any(ev.frame.data):result['nonzero_frames']+=1
        finally:await stream.aclose()
    @room.on('track_subscribed')
    def track(track,pub,participant):
        if track.kind==rtc.TrackKind.KIND_AUDIO:
            task=asyncio.create_task(consume(track));tasks.add(task);task.add_done_callback(tasks.discard)
    @room.on('participant_attributes_changed')
    def attributes(attrs,participant):
        nonlocal speaking
        if attrs.get('avatar.character'):result['avatars'].append(attrs['avatar.character'])
        state=attrs.get('lk.agent.state')
        if state:
            result['agent_states'].append(state)
            if state=='speaking':speaking=True
            if state=='listening' and speaking and result['nonzero_frames']>0:completed.set();speaking=False
    try:
        async with httpx.AsyncClient() as client:
            response=await client.post(base+'/api/token',json={});result['token_status']=response.status_code;response.raise_for_status();data=response.json()
        result['session_id']=data.get('telemetry',{}).get('context',{}).get('app_session_id')
        async with asyncio.timeout(90):
            await room.connect(data['serverUrl'],data['participantToken'])
            await completed.wait();result['greeting_completed']=True
            if scenario=='handoff':
                completed.clear()
                await room.local_participant.send_text('Esta es una prueba técnica sin datos personales. Transfiéreme con Nexus; quiero conocer los temas de la especialización en inteligencia artificial.',topic='lk.chat')
                # An acknowledgment can finish before the handoff. Wait for the target then its response.
                for _ in range(100):
                    if 'NEXO' in result['avatars']:break
                    await asyncio.sleep(.25)
                result['handoff_announced']='NEXO' in result['avatars']
                completed.clear()
                await completed.wait();result['followup_completed']=True
    except Exception as exc:result['error_type']=type(exc).__name__
    finally:
        await room.disconnect()
        pending=list(tasks)
        for task in pending:task.cancel()
        await asyncio.gather(*pending,return_exceptions=True)
    return result

async def inspect(base,result):
    env={k:v.strip().strip('\"\'') for line in (ROOT/'.env.voice').read_text().splitlines() if '=' in line and not line.startswith('#') for k,v in [line.split('=',1)]}
    async with httpx.AsyncClient() as client:
        response=await client.post(base+'/api/admin/login',json={'password':env['TELEMETRY_ADMIN_PASSWORD']},headers={'Origin':base})
        result['admin_login_status']=response.status_code
        response=await client.get(base+'/api/admin/sessions/'+str(result.get('session_id'))+'/events')
        result['events_status']=response.status_code
        if response.status_code==200:
            events=response.json()['items'];counts={}
            for e in events:counts[e['type']]=counts.get(e['type'],0)+1
            result['persisted_event_counts']=counts
            result['logical_agents']=sorted({e['agent_id'] for e in events if e.get('agent_id')})
            result['usage_providers']=sorted({e['payload']['provider'] for e in events if e['type']=='usage_recorded'})
            result['producer_health']=[e['payload'] for e in events if e['type']=='producer_health'][:1]

async def main(args):
    result=await run(args.base,args.scenario)
    await asyncio.sleep(6)
    try:await inspect(args.base,result)
    except Exception as exc:result['inspection_error']=type(exc).__name__
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if result.get('greeting_completed') and not result.get('error_type') else 1

if __name__=='__main__':
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',required=True)
    parser.add_argument('--base',default='http://localhost:3500')
    parser.add_argument('--scenario',choices=['greeting','handoff'],default='greeting')
    parser.add_argument('--output',required=True)
    raise SystemExit(asyncio.run(main(parser.parse_args())))
