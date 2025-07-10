graph TB
    %% Pipeline 1 - Fire Assessment Application
    subgraph Pipeline1 ["Fire Assessment Application - Pipeline 1"]
        S1[Sentinel-2<br/>10-20m/pixel<br/>RGB, NIR, R, SWIR bands]
        Timer1((Timer<br/>Monthly))
        API1[Pull data using<br/>Sentinel Hub API]
        Storage1[(Storage/Files)]
        GeoTIFF1[Multiband<br/>geoTIFF]
        NDVI1[NDVI and NBR<br/>calculation]
        Filter1[Select areas<br/>without exposed soil]
        Output1[Multiband geoTIFF<br/>and geoJSON]
        FinalStorage1[(Storage/Files)]
        
        S1 --> API1
        Timer1 --> API1
        API1 --> GeoTIFF1
        GeoTIFF1 --> Storage1
        Storage1 --> NDVI1
        NDVI1 --> Filter1
        Filter1 --> Output1
        Output1 --> FinalStorage1
    end

    %% Pipeline 2 - Fire Assessment Application
    subgraph Pipeline2 ["Fire Assessment Application - Pipeline 2"]
        Timer2((Timer<br/>Monthly))
        InputFiles[geoTIFF from<br/>weeks N and N-1]
        StorageInput[(Storage/Files)]
        Process2[Calculates difference<br/>and generate reports]
        GEE[Google Earth Engine<br/>API]
        Results2[Multiband geoTIFF<br/>and CSV report]
        StorageOutput2[(Storage/Files)]
        
        StorageInput --> InputFiles
        InputFiles --> Process2
        Timer2 --> Process2
        Process2 --> GEE
        GEE --> Results2
        Results2 --> StorageOutput2
    end

    %% Visualization Layer
    subgraph Visualization ["Visualization & User Access"]
        WebViz[Web Visualization Tool<br/>Filters by source, month,<br/>comparison between months, etc]
        GeneralUser[General Audience]
        
        subgraph FF1 ["Fundação Florestal"]
            QGIS1[Q-GIS<br/>Visualization tool]
            InternalUser1[Internal User]
            HighRes1[Georeferenced High<br/>Res images geoTIFF]
        end
        
        StorageOutput2 --> WebViz
        WebViz --> GeneralUser
        WebViz --> HighRes1
        HighRes1 --> QGIS1
        QGIS1 --> InternalUser1
    end

    %% Old System
    subgraph OldSystem ["OLD - Fire Assessment Application"]
        subgraph INPE ["INPE Data Processing"]
            SatINPE[Satellite Images<br/>INPE 10m/pixel<br/>RGB and NIR bands]
            APIINPE[API to pull<br/>information]
            NDVIINPE[NDVI<br/>calculation]
            Merge1((Merge))
            BandComp1[Script for<br/>Band composition]
            HighResINPE[Georeferenced High<br/>and Low Res images geoTIFF]
        end
        
        subgraph Copernicus ["Copernicus Data Processing"]
            SatCop[Satellite Images<br/>Copernicus 16m/pixel<br/>RGB, NIR and SWIR]
            WebScrape[Web Scraping<br/>for pulling data]
            NDVICop[NDVI and NBR<br/>calculation]
            Merge2((Merge))
            BandComp2[Script for<br/>Band composition]
            HighResCop[Georeferenced High<br/>and Low Res images geoTIFF]
        end
        
        Timer3((Timer<br/>Monthly))
        GEEOld[Google Earth Engine<br/>GEE]
        DatabaseOld[(Database/Metadata<br/>Storage/Files)]
        WebVizOld[Web Visualization Tool<br/>Filters by source, month,<br/>comparison between months, etc]
        GeneralUserOld[General Audience]
        
        subgraph FF2 ["Fundação Florestal"]
            QGIS2[Q-GIS<br/>Visualization tool]
            InternalUser2[Internal User]
            HighRes2[Georeferenced High<br/>Res images geoTIFF]
        end
        
        Timer3 --> SatINPE
        Timer3 --> SatCop
        SatINPE --> APIINPE
        APIINPE --> NDVIINPE
        NDVIINPE --> Merge1
        Merge1 --> BandComp1
        BandComp1 --> HighResINPE
        
        SatCop --> WebScrape
        WebScrape --> NDVICop
        NDVICop --> Merge2
        Merge2 --> BandComp2
        BandComp2 --> HighResCop
        
        Merge1 --> GEEOld
        Merge2 --> GEEOld
        GEEOld --> DatabaseOld
        DatabaseOld --> WebVizOld
        WebVizOld --> GeneralUserOld
        WebVizOld --> HighRes2
        HighRes2 --> QGIS2
        QGIS2 --> InternalUser2
    end

    %% Connect pipelines
    FinalStorage1 -.-> Pipeline2
    
    classDef satellite fill:#e1f5fe
    classDef processing fill:#fff3e0
    classDef storage fill:#ffebee
    classDef user fill:#f3e5f5
    classDef timer fill:#e8f5e8
    
    class S1,SatINPE,SatCop satellite
    class API1,NDVI1,Filter1,Process2,APIINPE,NDVIINPE,WebScrape,NDVICop,BandComp1,BandComp2 processing
    class Storage1,FinalStorage1,StorageInput,StorageOutput2,DatabaseOld storage
    class GeneralUser,InternalUser1,GeneralUserOld,InternalUser2 user
    class Timer1,Timer2,Timer3 timer