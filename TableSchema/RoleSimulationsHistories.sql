CREATE TABLE [dbo].[RoleSimulationsHistories]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [SimulationType] nvarchar(50) NOT NULL,
    [Date] datetime NOT NULL,
    [PerformedBy] nvarchar(100) NOT NULL,
    [SimulationParametersText] nvarchar(MAX) NOT NULL,
    [SimulationParametersXML] xml NOT NULL,
    [NumberOfRisks] int NOT NULL,
    [SimulationResults] xml NOT NULL
);
