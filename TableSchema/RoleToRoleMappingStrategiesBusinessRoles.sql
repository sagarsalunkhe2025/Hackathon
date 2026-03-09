CREATE TABLE [dbo].[RoleToRoleMappingStrategiesBusinessRoles]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [BusinessProcessPersonId] bigint NOT NULL,
    [RoleToRoleMappingStrategyId] bigint NOT NULL
);
