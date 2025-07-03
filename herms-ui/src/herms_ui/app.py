import sys
import herms
from PySide6.QtWidgets import QApplication, QMainWindow, QFrame

class UiApp(herms.App):
    title:str="herms"

    def __init__(self):
        pass

    def run(self) -> None:
        """
        実行します。
            """
        app = QApplication(sys.argv)
        window = MainWindow(self.title)
        window.show()
        sys.exit(app.exec())

# メインウィンドウのクラス
class MainWindow(QMainWindow):
    def __init__(self,title:str):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(800, 600)

class MainPanel(QFrame):
    def __init__(self):
        pass

# class App(tkinter.Tk):
#     def __init__(self,services):
#         super(App,self).__init__()
#         self.minsize(width=800,height=600)
#         self.title("Projman client")
#         self.frame=self._create_frame(services)
#         self.update_projects(services)

#     def _create_frame(self,services):
#         frame=tkinter.Frame(master=self)
#         toolbar=widget.Toolbar(frame)
#         for s in sorted(services.keys()):
#             mod=services[s]
#             for k,v in mod.global_command().items():
#                 toolbar.add_button(k,v)
#         toolbar.pack(fill=tkinter.X)
#         notebook=ttk.Notebook(frame)
#         self.main_panel=MainPanel(notebook,services)
#         notebook.add(self.main_panel,text='Main')
#         for s in sorted(services.keys()):
#             mod=services[s]
#             for c,v in mod.pages().items():
#                 notebook.add(v(notebook),text=c)
#         notebook.pack(expand=1,fill=tkinter.BOTH)
#         frame.pack(expand=1,fill=tkinter.BOTH)
#         return frame

#     def update_projects(self,services):
#         projects=sorted(app.app.projects.values(),key=lambda p: p.name)
#         self.main_panel.update(projects)
        

# class MainPanel(tkinter.Frame):
#     def __init__(self,root,services):
#         super(MainPanel,self).__init__(root,name='mainPanel')
#         self.services=services
#         canvas=tkinter.Canvas(self)
#         self.list=tkinter.Frame(canvas)
#         scrollbar=tkinter.Scrollbar(self,orient=tkinter.VERTICAL)
#         canvas.config(yscrollcommand=scrollbar.set)
#         scrollbar.config(command=canvas.yview)
#         scrollbar.pack(side=tkinter.RIGHT,fill=tkinter.Y)
#         self._list_id=canvas.create_window((4,4),window=self.list,anchor=tkinter.N+tkinter.W)
#         canvas.pack(side=tkinter.LEFT,expand=True,fill=tkinter.BOTH)
#         self.list.columnconfigure(0,weight=1)
#         def onMouseWheel(event):
#             canvas.yview_scroll(-1*event.delta,tkinter.UNITS)
#         self.bind_all("<MouseWheel>",onMouseWheel)
        

#         def onFrameConfigure(event):
#             canvas.configure(scrollregion=self.list.bbox("all"))
#         self.list.bind("<Configure>",onFrameConfigure)

#         self._project_panels=[]

#     def update(self,projects):
#         while len(projects)>len(self._project_panels):
#             panel=self.create_project_panel()
#             panel.grid(row=len(self._project_panels),column=0,sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)
#             self._project_panels.append(panel)
#         while len(projects)<len(self._project_panels):
#             self._project_panels.pop().destroy()
#         for i in range(0,len(projects)):
#             self._project_panels[i].update(projects[i])

#     def create_project_panel(self):
#         panel=ProjectPanel(self.list,self)
#         for m in self.services.items():
#             mp=m.project_panel(panel)
#             if mp is not None:
#                 panel.register(mp)
#         return panel
        
# class ProjectPanel(tkinter.Frame):
#     maxcol=3
#     def __init__(self,root,parent):
#         super(ProjectPanel,self).__init__(root,bd=3,relief=tkinter.RAISED)
#         self.label=tkinter.Label(self)
#         self.label.grid(row=0,column=0)
#         buttons=widget.Toolbar(self)
#         buttons.add_button('Dir',self.show_explorer)
#         buttons.add_button('Sync',self.sync)
#         buttons.grid(row=0,column=1,sticky=tkinter.W+tkinter.N)
#         self.project=None
#         self.parent=parent
#         self.panels=[]
#         for i in range(0,ProjectPanel.maxcol):
#             self.grid_columnconfigure(i,minsize=250,weight=1)
#         self._row=1
#         self._col=0

#     def register(self,panel):
#         if panel is not None:
#             self.panels.append(panel)
#             panel.grid(row=self._row,column=self._col,sticky=tkinter.N+tkinter.S+tkinter.E+tkinter.W)
#             self._col+=1
#             if self._col==ProjectPanel.maxcol:
#                 self._col=0
#                 self._row+=1

#     def update(self,proj):
#         self.project=proj
#         self.label["text"]=proj.name
#         for p in self.panels:
#             p.update(proj)

#     def show_explorer(self):
#         subprocess.call(["explorer",os.path.normpath(self.parent.client.project_path(self.project))])

#     def sync(self):
#         job=widget.JobWindow()
#         job.run(self,self.run_sync)
#         self.update(self.project)
        
#     def run_sync(self,job):
#         if self.project is not None:
#             self.parent.client.sync(job,self.project)
#         job.endq()
