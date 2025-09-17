"use client"
import { createContext , useContext , useState , ReactNode } from "react";

interface Agent{
  _id?: string;
  name: string;
  description?: string;
  org?: string;
  model?: string;
  temperature?: number;
  tools: string[];
  created_at?: string;
  updated_at?: string;
}

type TAgentsContext = {
      agent: Agent ;
      setField : <K extends keyof Agent>(key: K, value: Agent[K])=> void ;
      // toggleTool : (tool : string )=>void ;
      reset : ()=>void ;
}

const AgentContext = createContext<TAgentsContext | undefined>(undefined)

export function AgentProvider({ children }:{children : ReactNode}){
      const [agent , setAgent] = useState<Agent>({
             name: "",
             description: "",
             model: "gpt-3.5-turbo",
             temperature: 0.7,
             tools: [] ,
      })

      const setField : TAgentsContext["setField"] = (key , value) =>{
            setAgent((prev)=>({...prev , [key] : value}))
      }

      // const toggleTool : TAgentsContext["toggleTool"] = (tool)=>{
      //       setAgent((prev)=>({...prev , tools: prev.tools.includes(tool) ? prev.tools.filter((t)=>t !== tool) : [...prev.tools , tool]}))
      // }

const reset = () =>
    setAgent({
      name: "",
      description: "",
      model: "gpt-3.5-turbo",
      temperature: 0.7,
      tools: [],
    });

    return(
      <AgentContext.Provider value={{agent , setField , reset}}>
            {children}
      </AgentContext.Provider>
    )
}

export function useAgent(){
 const context = useContext(AgentContext);
  if (!context) {
    throw new Error("useAgent باید داخل AgentProvider استفاده شود");
  }
  return context;
}