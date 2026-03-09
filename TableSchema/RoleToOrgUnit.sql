CREATE TABLE [dbo].[RoleToOrgUnit]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [OrganizationStructureId] bigint NOT NULL,
    [RoleId] bigint NOT NULL,
    [CustomerId] bigint NOT NULL
);
