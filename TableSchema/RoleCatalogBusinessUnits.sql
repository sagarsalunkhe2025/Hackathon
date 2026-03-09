CREATE TABLE [dbo].[RoleCatalogBusinessUnits]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [Name] nvarchar(200) NOT NULL,
    [CustomerId] bigint NULL,
    [Description] nvarchar(500) NOT NULL
);
