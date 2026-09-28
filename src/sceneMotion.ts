import {useEffect, useRef, type MouseEvent, type RefObject} from 'react';

export function goToSection(event: MouseEvent<HTMLAnchorElement>, id: string) {
  const element=document.getElementById(id);
  if(!element)return;
  event.preventDefault();
  element.focus({preventScroll:true});
  element.scrollIntoView({block:'start',behavior:event.detail===0||matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}

// Native scrolling drives a bounded visual scene. No wheel interception, artificial
// inertia, timers, or continuously running animation loop.
export function useScrollScene(ref:RefObject<HTMLElement|null>, update:(progress:number,reduced:boolean)=>void) {
  const latest=useRef(update);latest.current=update;
  useEffect(()=>{
    const query=matchMedia('(prefers-reduced-motion: reduce)');let frame=0;
    const render=()=>{frame=0;const e=ref.current;if(!e)return;const r=e.getBoundingClientRect();
      if(r.bottom<0||r.top>innerHeight)return;
      const progress=Math.max(0,Math.min(1,-r.top/Math.max(1,r.height-innerHeight)));
      latest.current(progress,query.matches);
    };
    const schedule=()=>{if(!frame)frame=requestAnimationFrame(render)};
    addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);query.addEventListener('change',schedule);render();
    return()=>{cancelAnimationFrame(frame);removeEventListener('scroll',schedule);removeEventListener('resize',schedule);query.removeEventListener('change',schedule)};
  },[ref]);
}
