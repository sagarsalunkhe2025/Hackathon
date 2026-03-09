CREATE TABLE [dbo].[RoleToRoleMappingStrategies]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [CustomerId] bigint NOT NULL,
    [Name] nvarchar(50) NOT NULL,
    [IsActive] bit NOT NULL
);
