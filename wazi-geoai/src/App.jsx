import { useState } from 'react'

import MapView from './components/MapView'
import Sidebar from './components/Sidebar'
import Legend from './components/Legend'
import Breadcrumb from './components/Breadcrumb'
import CommentSection from './components/CommentSection'

import './styles.css'

export default function App() {

  const [selectedProject, setSelectedProject] =
    useState(null)

  return (
    <div className="app-container">

      <Sidebar />

      <div className="main-content">

        <div className="map-wrapper">

          <Breadcrumb />

          <MapView
            setSelectedProject={
              setSelectedProject
            }
          />

          <Legend />

        </div>

        {selectedProject && (

          <CommentSection
            project={selectedProject}
            closeComments={() =>
              setSelectedProject(null)
            }
          />

        )}

      </div>

    </div>
  )
}