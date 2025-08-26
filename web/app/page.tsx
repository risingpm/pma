"use client";
import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Progress } from "../components/ui/progress";
import { createProject, listProjects, getOnboarding, patchOnboarding, commitOnboarding, type Onboarding } from "../lib/api";
import { toast } from "sonner";

export default function Page() {
  const [projects, setProjects] = useState<{id:string; name:string}[]>([]);
  const [projectId, setProjectId] = useState<string>("");
  const [ob, setOb] = useState<Onboarding | null>(null);
  const [step, setStep] = useState(1);
  const steps = 6;

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((e) => {
        console.error("Failed to load projects", e);
        toast.error("Failed to load projects");
      });
  }, []);

  useEffect(() => {
    if (!projectId) return;
    getOnboarding(projectId)
      .then(setOb)
      .catch((e) => {
        console.error("Failed to load onboarding", e);
        toast.error("Failed to load onboarding");
      });
  }, [projectId]);

  const progress = useMemo(() => Math.round((step/steps)*100), [step]);

  async function save(patch: Partial<Onboarding>) {
    if (!projectId) return;
    const next = await patchOnboarding(projectId, patch);
    setOb(next);
    return next;
  }

  async function handleCommit() {
    if (!projectId) return;
    try {
      const res = await commitOnboarding(projectId);
      setOb(res);
      toast.success("Onboarding committed!");
    } catch (e: unknown) {
      const err = e as any;
      console.error("Commit failed", err);
      toast.error(err?.response?.data?.detail || "Commit failed");
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">PM Agent — Onboarding</h1>
        <div className="flex gap-2">
          <select className="h-10 rounded-xl border px-3 text-sm" value={projectId} onChange={(e)=>setProjectId(e.target.value)}>
            <option value="">Select a project…</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <Button
            variant="outline"
            onClick={async () => {
              const name = prompt("Project name?");
              if (!name) return;
              try {
                const meta = await createProject(name);
                toast.success("Project created");
                const list = await listProjects();
                setProjects(list);
                setProjectId(meta.id);
              } catch (e: unknown) {
                const err = e as any;
                const msg = err?.response?.data?.detail || err?.message || "Create failed";
                console.error("Create project error", err);
                toast.error(`Create failed: ${msg}`);
              }
            }}
          >
            New Project
          </Button>
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Step {step} of {steps}</CardTitle>
          <Progress value={progress} />
        </CardHeader>
        <CardContent>
          {!projectId && <p className="text-sm text-gray-600">Create or select a project to begin.</p>}
          {projectId && ob && (
            <AnimatePresence mode="wait">
              {step === 1 && (
                <motion.div key="s1" initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-8}} className="space-y-4">
                  <h3 className="font-medium">1) Basics</h3>
                  <Input id="name-input" placeholder="Project Name *" defaultValue={ob.identity?.name || ""} onBlur={(e)=>save({ identity: { ...(ob.identity||{}), name: e.target.value } })} />
                  <Input id="one-line-input" placeholder="One-line (optional)" defaultValue={ob.identity?.one_line || ""} onBlur={(e)=>save({ identity: { ...(ob.identity||{}), one_line: e.target.value } })} />
                  <Textarea id="problem-input" placeholder="Problem Statement *" defaultValue={ob.intent?.problem_statement || ""} onBlur={(e)=>save({ intent: { ...(ob.intent||{}), problem_statement: e.target.value } })} />
                  <div className="flex justify-end">
                    <Button onClick={async()=>{
                      const name = (document.getElementById("name-input") as HTMLInputElement)?.value?.trim();
                      const oneLine = (document.getElementById("one-line-input") as HTMLInputElement)?.value || "";
                      const problem = (document.getElementById("problem-input") as HTMLTextAreaElement)?.value?.trim();
                      if (!name || !problem) { toast.error("Name and Problem Statement are required"); return; }
                      await save({ identity: { ...(ob.identity||{}), name, one_line: oneLine }, intent: { ...(ob.intent||{}), problem_statement: problem } });
                      setStep(2);
                    }}>Save & Continue →</Button>
                  </div>
                </motion.div>
              )}

              {step === 2 && (
                <motion.div key="s2" initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-8}} className="space-y-4">
                  <h3 className="font-medium">2) Direction</h3>
                  <Input placeholder="North Star (optional)" defaultValue={ob.intent?.north_star || ""} onBlur={(e)=>save({ intent: { ...(ob.intent||{}), north_star: e.target.value } })} />
                  <Textarea placeholder="Business Objectives (comma separated)" defaultValue={(ob.intent?.business_objectives||[]).join(", ")} onBlur={(e)=>save({ intent: { ...(ob.intent||{}), business_objectives: e.target.value.split(",").map(s=>s.trim()).filter(Boolean) } })} />
                  <Textarea placeholder="Out of Scope (one per line)" defaultValue={(ob.intent?.out_of_scope||[]).join("\n")} onBlur={(e)=>save({ intent: { ...(ob.intent||{}), out_of_scope: e.target.value.split("\n").map(s=>s.trim()).filter(Boolean) } })} />
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={()=>setStep(1)}>← Back</Button>
                    <Button onClick={()=>setStep(3)}>Save & Continue →</Button>
                  </div>
                </motion.div>
              )}

              {step === 3 && (
                <motion.div key="s3" initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-8}} className="space-y-4">
                  <h3 className="font-medium">3) Users & Use Cases</h3>
                  <div className="flex gap-2">
                    <Input placeholder="Add persona (name)" onKeyDown={async(e)=>{
                      if (e.key === 'Enter') {
                        const v = (e.target as HTMLInputElement).value.trim(); if (!v) return;
                        const personas = [...(ob.users?.personas||[]), { name: v }];
                        await save({ users: { personas } } as any);
                        (e.target as HTMLInputElement).value = '';
                        toast.success("Persona added");
                      }
                    }} />
                    <Button variant="outline" onClick={()=>toast.info((ob.users?.personas||[]).map(p=>p.name).join(', ')||'No personas yet')}>View</Button>
                  </div>
                  <div className="space-y-2">
                    <Input placeholder="Use case title" id="tuc-title" />
                    <Textarea placeholder="Success criteria (one per line)" id="tuc-sc" />
                    <Button variant="outline" onClick={async()=>{
                      const title = (document.getElementById('tuc-title') as HTMLInputElement).value.trim();
                      const scRaw = (document.getElementById('tuc-sc') as HTMLTextAreaElement).value;
                      if (!title) return toast.error('Title required');
                      const top_use_cases = [...(ob.intent?.top_use_cases||[]), { title, success_criteria: scRaw.split('\n').map(s=>s.trim()).filter(Boolean) }];
                      await save({ intent: { ...(ob.intent||{}), top_use_cases } });
                      (document.getElementById('tuc-title') as HTMLInputElement).value = '';
                      (document.getElementById('tuc-sc') as HTMLTextAreaElement).value = '';
                      toast.success('Use case added');
                    }}>Add Use Case</Button>
                  </div>
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={()=>setStep(2)}>← Back</Button>
                    <Button onClick={()=>setStep(4)}>Save & Continue →</Button>
                  </div>
                </motion.div>
              )}

              {step === 4 && (
                <motion.div key="s4" initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-8}} className="space-y-6">
                  <h3 className="font-medium">4) Metrics — Primary Objectives & Guardrails</h3>

                  <div className="rounded-2xl border p-4">
                    <h4 className="mb-2 font-medium">Primary Objective</h4>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <Input placeholder="Metric name" id="m-name" />
                      <Input placeholder="Unit" id="m-unit" />
                      <Input placeholder="Definition" id="m-def" className="sm:col-span-2" />
                      <Input placeholder="Baseline (number)" id="m-base" />
                      <Input placeholder="Target (number)" id="m-target" />
                      <Input placeholder="Target date (YYYY-MM-DD)" id="m-date" />
                    </div>
                    <div className="mt-3">
                      <Button variant="outline" onClick={async()=>{
                        const po = [...(ob.metrics?.primary_objectives||[]), {
                          name: (document.getElementById('m-name') as HTMLInputElement).value,
                          unit: (document.getElementById('m-unit') as HTMLInputElement).value || null,
                          definition: (document.getElementById('m-def') as HTMLInputElement).value || null,
                          baseline: parseFloat((document.getElementById('m-base') as HTMLInputElement).value) || null,
                          target: parseFloat((document.getElementById('m-target') as HTMLInputElement).value) || null,
                          target_date: (document.getElementById('m-date') as HTMLInputElement).value || null,
                        }];
                        await save({ metrics: { ...(ob.metrics||{}), primary_objectives: po } });
                        toast.success('Metric added');
                      }}>Add Metric</Button>
                    </div>
                  </div>

                  <div className="rounded-2xl border p-4">
                    <h4 className="mb-2 font-medium">Guardrail</h4>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <Input placeholder="Guardrail name" id="g-name" />
                      <Input placeholder="Unit" id="g-unit" />
                      <Input placeholder="Definition" id="g-def" className="sm:col-span-2" />
                      <Input placeholder="Threshold (number)" id="g-thr" />
                      <select id="g-dir" className="h-10 rounded-xl border px-3 text-sm">
                        <option value="min">min</option>
                        <option value="max">max</option>
                      </select>
                    </div>
                    <div className="mt-3">
                      <Button variant="outline" onClick={async()=>{
                        const gr = [...(ob.metrics?.guardrails||[]), {
                          name: (document.getElementById('g-name') as HTMLInputElement).value,
                          unit: (document.getElementById('g-unit') as HTMLInputElement).value || null,
                          definition: (document.getElementById('g-def') as HTMLInputElement).value || null,
                          threshold: parseFloat((document.getElementById('g-thr') as HTMLInputElement).value) || null,
                          direction: (document.getElementById('g-dir') as HTMLSelectElement).value as any,
                        }];
                        await save({ metrics: { ...(ob.metrics||{}), guardrails: gr } });
                        toast.success('Guardrail added');
                      }}>Add Guardrail</Button>
                    </div>
                  </div>

                  <div className="flex justify-between">
                    <Button variant="outline" onClick={()=>setStep(3)}>← Back</Button>
                    <Button onClick={()=>setStep(5)}>Save & Continue →</Button>
                  </div>
                </motion.div>
              )}

              {step === 5 && (
                <motion.div key="s5" initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-8}} className="space-y-4">
                  <h3 className="font-medium">5) Milestones</h3>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Input placeholder="Milestone name" id="ms-name" />
                    <Input placeholder="Date (YYYY-MM-DD)" id="ms-date" />
                    <Textarea placeholder="Exit criteria (one per line)" id="ms-ec" className="sm:col-span-2" />
                  </div>
                  <Button variant="outline" onClick={async()=>{
                    const ms = [...(ob.delivery?.milestones||[]), {
                      name: (document.getElementById('ms-name') as HTMLInputElement).value,
                      date: (document.getElementById('ms-date') as HTMLInputElement).value || null,
                      exit_criteria: (document.getElementById('ms-ec') as HTMLTextAreaElement).value.split('\n').map(s=>s.trim()).filter(Boolean)
                    }];
                    await save({ delivery: { ...(ob.delivery||{}), milestones: ms } });
                    toast.success('Milestone added');
                  }}>Add Milestone</Button>
                  <div className="flex justify-between">
                    <Button variant="outline" onClick={()=>setStep(4)}>← Back</Button>
                    <Button onClick={()=>setStep(6)}>Save & Continue →</Button>
                  </div>
                </motion.div>
              )}

              {step === 6 && (
                <motion.div key="s6" initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-8}} className="space-y-4">
                  <h3 className="font-medium">6) Artifacts & Review</h3>
                  <Textarea placeholder="PRD links (one per line)" defaultValue={(ob.artifacts?.prds||[]).join('\n')} onBlur={(e)=>save({ artifacts: { ...(ob.artifacts||{}), prds: e.target.value.split('\n').map(s=>s.trim()).filter(Boolean) } })} />
                  <Textarea placeholder="Design links (one per line)" defaultValue={(ob.artifacts?.designs||[]).join('\n')} onBlur={(e)=>save({ artifacts: { ...(ob.artifacts||{}), designs: e.target.value.split('\n').map(s=>s.trim()).filter(Boolean) } })} />
                  <Textarea placeholder="Tech doc links (one per line)" defaultValue={(ob.artifacts?.tech_docs||[]).join('\n')} onBlur={(e)=>save({ artifacts: { ...(ob.artifacts||{}), tech_docs: e.target.value.split('\n').map(s=>s.trim()).filter(Boolean) } })} />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select id="ds-type" className="h-10 rounded-xl border px-3 text-sm">
                      <option value="none">data schema: none</option>
                      <option value="link">link</option>
                      <option value="inline">inline</option>
                    </select>
                    <Input id="ds-val" placeholder="Data schema URL or inline value" />
                  </div>
                  <Button variant="outline" onClick={async()=>{
                    const typeEl = document.getElementById('ds-type') as HTMLSelectElement;
                    const valEl = document.getElementById('ds-val') as HTMLInputElement;
                    const data_schema = typeEl.value === 'none' ? null : { type: typeEl.value as any, value: valEl.value };
                    await save({ artifacts: { ...(ob.artifacts||{}), data_schema } });
                    toast.success('Artifacts saved');
                  }}>Save Artifacts</Button>

                  <div className="rounded-2xl border p-4">
                    <p className="text-sm text-gray-600">Confidence Index: <span className="font-medium">{Math.round((ob.derived?.confidence_index||0)*100)}%</span></p>
                    {(ob.derived?.next_best_actions||[]).length > 0 && (
                      <ul className="mt-2 list-disc pl-6 text-sm">
                        {ob.derived!.next_best_actions!.map((a,i)=> <li key={i}>{a}</li>)}
                      </ul>
                    )}
                  </div>

                  <div className="flex justify-between">
                    <Button variant="outline" onClick={()=>setStep(5)}>← Back</Button>
                    <Button onClick={handleCommit}>✅ Commit Onboarding</Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
