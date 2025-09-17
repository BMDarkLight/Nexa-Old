"use client";

import {
  ChevronLeft,
  ChevronRight,
  DeleteIcon,
  Edit,
  Trash,
  Trash2,
  type LucideIcon,
} from "lucide-react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";

export function NavMain({
  items,
  onDelete,
}: {
  items: {
    title: string;
    url: string;
    icon?: LucideIcon;
    isActive?: boolean;
    items?: {
      title: string;
      url: string;
      id: string ;
    }[];
  }[];
  onDelete?: (sessionId:string) => void
}) {
  return (
    <SidebarGroup>
      <SidebarMenu>
        {items.map((item) => (
          <Collapsible
            key={item.title}
            asChild
            defaultOpen={item.isActive}
            className="group/collapsible"
          >
            <SidebarMenuItem>
              <CollapsibleTrigger asChild>
                <SidebarMenuButton
                  tooltip={item.title}
                  className="text-[#71717A] text-base"
                >
                  {item.icon && <item.icon />}
                  <span>{item.title}</span>
                  <ChevronLeft className="mr-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-[-90deg]" />
                </SidebarMenuButton>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <SidebarMenuSub>
                  {item.items?.map((subItem) => (
                    <SidebarMenuSubItem key={subItem.title}>
                      <SidebarMenuSubButton asChild className="text-[#71717A]">
                        <div className="flex justify-between items-center text-base">
                          <div className="hover:text-sidebar-accent-foreground active:text-sidebar-accent-foreground">
                            <a href={subItem.url}>
                              <span>{subItem.title}</span>
                            </a>
                          </div>
                          <div className="flex items-center gap-2">
                            <a href="" className="hover:text-green-400">
                              <Edit size={18} />
                            </a>
                            <a href="#" className="hover:text-red-400" onClick={(e)=>{
                              e.preventDefault()
                              if(onDelete && subItem.id){
                                onDelete(subItem.id)
                              }
                            }}>
                              <Trash2 size={18} />
                            </a>
                          </div>
                        </div>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </CollapsibleContent>
            </SidebarMenuItem>
          </Collapsible>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
