import { useState, useEffect, useCallback } from 'react';
import { organizationsAPI } from '../services/api';

interface Organization {
  id: number;
  name: string;
  slug: string;
  role: string;
  owner_user_id: number;
  email?: string;
  phone?: string;
  active: boolean;
}

interface Member {
  id: number;
  organization_id: number;
  user_id: number | null;
  role: string;
  active: boolean;
  invited_email: string | null;
  invited_at: string | null;
  joined_at: string | null;
  user_name: string | null;
  user_email: string | null;
}

const ROLE_LABELS: Record<string, string> = {
  owner: 'Owner',
  admin: 'Admin',
  finance: 'Finance',
  viewer: 'Viewer',
};

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-purple-100 text-purple-800',
  admin: 'bg-blue-100 text-blue-800',
  finance: 'bg-teal-100 text-teal-800',
  viewer: 'bg-gray-100 text-gray-800',
};

export default function OrganizationSection() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [membersLoading, setMembersLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddMember, setShowAddMember] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('viewer');
  const [showCreateOrg, setShowCreateOrg] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');

  const fetchOrganizations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await organizationsAPI.list();
      const orgs = res.data.items || [];
      setOrganizations(orgs);
      if (orgs.length > 0 && !selectedOrg) {
        setSelectedOrg(orgs[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao carregar organizações');
    } finally {
      setLoading(false);
    }
  }, [selectedOrg]);

  const fetchMembers = useCallback(async (orgId: number) => {
    try {
      setMembersLoading(true);
      const res = await organizationsAPI.listMembers(orgId);
      setMembers(res.data.items || []);
    } catch (err: any) {
      setMembers([]);
    } finally {
      setMembersLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  useEffect(() => {
    if (selectedOrg) {
      fetchMembers(selectedOrg.id);
    }
  }, [selectedOrg, fetchMembers]);

  const canManageMembers = selectedOrg && (selectedOrg.role === 'owner' || selectedOrg.role === 'admin');

  const handleAddMember = async () => {
    if (!selectedOrg || !newMemberEmail.trim()) return;
    try {
      await organizationsAPI.addMember(selectedOrg.id, { email: newMemberEmail, role: newMemberRole });
      setNewMemberEmail('');
      setShowAddMember(false);
      fetchMembers(selectedOrg.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao adicionar membro');
    }
  };

  const handleUpdateRole = async (memberId: number, newRole: string) => {
    if (!selectedOrg) return;
    try {
      await organizationsAPI.updateMember(selectedOrg.id, memberId, { role: newRole });
      fetchMembers(selectedOrg.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao atualizar papel');
    }
  };

  const handleDeactivateMember = async (memberId: number) => {
    if (!selectedOrg) return;
    try {
      await organizationsAPI.deactivateMember(selectedOrg.id, memberId);
      fetchMembers(selectedOrg.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao desativar membro');
    }
  };

  const handleCreateOrg = async () => {
    if (!newOrgName.trim()) return;
    try {
      await organizationsAPI.create({ name: newOrgName });
      setNewOrgName('');
      setShowCreateOrg(false);
      fetchOrganizations();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erro ao criar organização');
    }
  };

  if (loading) {
    return (
      <section data-testid="organization-section" className="mt-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <p className="text-gray-500">Carregando organizações...</p>
      </section>
    );
  }

  return (
    <section data-testid="organization-section" className="mt-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">Organização & Membros</h2>
        {organizations.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              data-testid="organization-switcher"
              value={selectedOrg?.id || ''}
              onChange={(e) => {
                const org = organizations.find(o => o.id === parseInt(e.target.value));
                setSelectedOrg(org || null);
              }}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              {organizations.map(org => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${selectedOrg ? ROLE_COLORS[selectedOrg.role] || 'bg-gray-100 text-gray-800' : ''}`}>
              {selectedOrg ? ROLE_LABELS[selectedOrg.role] || selectedOrg.role : ''}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 font-bold">×</button>
        </div>
      )}

      {organizations.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-gray-500 mb-4">Nenhuma organização encontrada.</p>
          <button
            onClick={() => setShowCreateOrg(true)}
            className="rounded-md bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
          >
            Criar Organização
          </button>
        </div>
      ) : (
        <>
          {/* Organization info */}
          {selectedOrg && (
            <div data-testid="organization-info" className="mb-6 rounded-md bg-gray-50 p-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-semibold text-gray-700">Nome:</span>{' '}
                  <span className="text-gray-900">{selectedOrg.name}</span>
                </div>
                <div>
                  <span className="font-semibold text-gray-700">Slug:</span>{' '}
                  <span className="text-gray-600">{selectedOrg.slug}</span>
                </div>
                {selectedOrg.email && (
                  <div>
                    <span className="font-semibold text-gray-700">Email:</span>{' '}
                    <span className="text-gray-900">{selectedOrg.email}</span>
                  </div>
                )}
                {selectedOrg.phone && (
                  <div>
                    <span className="font-semibold text-gray-700">Telefone:</span>{' '}
                    <span className="text-gray-900">{selectedOrg.phone}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Members section */}
          <div data-testid="organization-members">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-800">Membros</h3>
              {canManageMembers && (
                <button
                  onClick={() => setShowAddMember(!showAddMember)}
                  className="rounded-md bg-teal-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
                  data-testid="add-member-button"
                >
                  {showAddMember ? 'Cancelar' : '+ Adicionar Membro'}
                </button>
              )}
            </div>

            {showAddMember && canManageMembers && (
              <div className="mb-4 flex gap-2 rounded-md border border-gray-200 p-3">
                <input
                  type="email"
                  placeholder="email@exemplo.com"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-teal-500 focus:outline-none"
                  data-testid="new-member-email"
                />
                <select
                  value={newMemberRole}
                  onChange={(e) => setNewMemberRole(e.target.value)}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                  data-testid="new-member-role"
                >
                  <option value="viewer">Viewer</option>
                  <option value="finance">Finance</option>
                  <option value="admin">Admin</option>
                </select>
                <button
                  onClick={handleAddMember}
                  className="rounded-md bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
                  data-testid="confirm-add-member"
                >
                  Adicionar
                </button>
              </div>
            )}

            {membersLoading ? (
              <p className="text-gray-500">Carregando membros...</p>
            ) : members.length === 0 ? (
              <p className="text-gray-500">Nenhum membro encontrado.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead>
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Nome</th>
                      <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Email</th>
                      <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Papel</th>
                      <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                      {canManageMembers && <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Ações</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {members.map((member) => (
                      <tr key={member.id} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-sm text-gray-900">
                          {member.user_name || member.invited_email || '—'}
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-600">
                          {member.user_email || member.invited_email || '—'}
                        </td>
                        <td className="px-3 py-2 text-sm">
                          {canManageMembers && member.role !== 'owner' ? (
                            <select
                              value={member.role}
                              onChange={(e) => handleUpdateRole(member.id, e.target.value)}
                              className="rounded border border-gray-300 px-2 py-0.5 text-xs"
                              data-testid={`member-role-select-${member.id}`}
                            >
                              <option value="viewer">Viewer</option>
                              <option value="finance">Finance</option>
                              <option value="admin">Admin</option>
                            </select>
                          ) : (
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_COLORS[member.role] || 'bg-gray-100 text-gray-800'}`}>
                              {ROLE_LABELS[member.role] || member.role}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-sm">
                          <span className={`rounded-full px-2 py-0.5 text-xs ${member.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {member.active ? 'Ativo' : 'Inativo'}
                          </span>
                        </td>
                        {canManageMembers && (
                          <td className="px-3 py-2 text-right">
                            {member.role !== 'owner' && member.active && (
                              <button
                                onClick={() => handleDeactivateMember(member.id)}
                                className="text-xs text-red-600 hover:text-red-800"
                                data-testid={`deactivate-member-${member.id}`}
                              >
                                Desativar
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Create new org (discreet) */}
          <div className="mt-6 border-t border-gray-100 pt-4">
            <button
              onClick={() => setShowCreateOrg(!showCreateOrg)}
              className="text-sm text-teal-600 hover:text-teal-800"
            >
              {showCreateOrg ? 'Cancelar' : '+ Criar nova organização'}
            </button>
            {showCreateOrg && (
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  placeholder="Nome da organização"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-teal-500 focus:outline-none"
                  data-testid="new-org-name"
                />
                <button
                  onClick={handleCreateOrg}
                  className="rounded-md bg-teal-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-teal-700"
                  data-testid="confirm-create-org"
                >
                  Criar
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
